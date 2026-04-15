#!/bin/bash

set -euo pipefail

# Configuration
readonly SCRIPT_NAME="$(basename "$0")"
readonly TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
readonly LOG_FILE="${LOG_FILE:-/tmp/aws_deploy_${TIMESTAMP}.log}"

# Default values
AWS_REGION="${AWS_REGION:-us-east-1}"
AWS_PROFILE="${AWS_PROFILE:-default}"
DEPLOYMENT_ENV="${DEPLOYMENT_ENV:-development}"
S3_BUCKET="${S3_BUCKET:-}"
CLOUDFORMATION_STACK="${CLOUDFORMATION_STACK:-}"
ECS_CLUSTER="${ECS_CLUSTER:-}"
ECS_SERVICE="${ECS_SERVICE:-}"
LAMBDA_FUNCTION="${LAMBDA_FUNCTION:-}"
DRY_RUN="${DRY_RUN:-false}"

# Colors for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly NC='\033[0m'

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1" | tee -a "$LOG_FILE"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
}

# Error handling
trap_error() {
    local exit_code=$?
    log_error "Script failed with exit code $exit_code on line $1"
    cleanup
    exit $exit_code
}

cleanup() {
    log_info "Cleaning up temporary resources..."
    if [[ -n "${TEMP_DIR:-}" && -d "$TEMP_DIR" ]]; then
        rm -rf "$TEMP_DIR"
    fi
}

trap 'trap_error $LINENO' ERR
trap cleanup EXIT

# Check dependencies
check_dependencies() {
    local deps=("aws" "jq")
    for cmd in "${deps[@]}"; do
        if ! command -v "$cmd" &> /dev/null; then
            log_error "$cmd is required but not installed"
            exit 1
        fi
    done
}

# Validate AWS credentials
validate_aws_credentials() {
    log_info "Validating AWS credentials..."
    
    # Check if running in CI/CD environment
    if [[ -n "${CI:-}" || -n "${GITHUB_ACTIONS:-}" || -n "${GITLAB_CI:-}" || -n "${JENKINS_URL:-}" ]]; then
        log_info "Running in CI/CD environment"
        
        # Check for IAM role credentials (EC2/ECS/Lambda)
        if curl -s --connect-timeout 2 http://169.254.169.254/latest/meta-data/iam/security-credentials/ &> /dev/null; then
            log_info "Using IAM instance profile credentials"
            unset AWS_PROFILE
        # Check for environment variable credentials
        elif [[ -n "${AWS_ACCESS_KEY_ID:-}" && -n "${AWS_SECRET_ACCESS_KEY:-}" ]]; then
            log_info "Using environment variable credentials"
            unset AWS_PROFILE
        else
            log_error "No AWS credentials found in CI/CD environment"
            exit 1
        fi
    else
        # Local development environment
        log_info "Running in local development environment"
        
        # Check for environment variable credentials first
        if [[ -n "${AWS_ACCESS_KEY_ID:-}" && -n "${AWS_SECRET_ACCESS_KEY:-}" ]]; then
            log_info "Using environment variable credentials"
            unset AWS_PROFILE
        # Check for AWS profile
        elif [[ -n "$AWS_PROFILE" ]]; then
            if ! aws configure list --profile "$AWS_PROFILE" &> /dev/null; then
                log_error "AWS profile '$AWS_PROFILE' not found"
                exit 1
            fi
            log_info "Using AWS profile: $AWS_PROFILE"
        # Check for default credentials
        elif aws sts get-caller-identity &> /dev/null; then
            log_info "Using default AWS credentials"
        else
            log_error "No valid AWS credentials found"
            log_info "Please set AWS_PROFILE or configure AWS credentials"
            exit 1
        fi
    fi
    
    # Verify credentials work
    if ! AWS_CALLER_IDENTITY=$(aws sts get-caller-identity 2>&1); then
        log_error "Failed to verify AWS credentials: $AWS_CALLER_IDENTITY"
        exit 1
    fi
    
    ACCOUNT_ID=$(echo "$AWS_CALLER_IDENTITY" | jq -r '.Account')
    USER_ARN=$(echo "$AWS_CALLER_IDENTITY" | jq -r '.Arn')
    
    log_info "Authenticated as: $USER_ARN"
    log_info "AWS Account: $ACCOUNT_ID"
    log_info "Region: $AWS_REGION"
}

# S3 deployment function
deploy_to_s3() {
    local source_path="$1"
    local target_bucket="$2"
    local target_prefix="${3:-}"
    
    if [[ ! -e "$source_path" ]]; then
        log_error "Source path does not exist: $source_path"
        return 1
    fi
    
    log_info "Deploying to S3 bucket: $target_bucket/$target_prefix"
    
    # Check if bucket exists
    if ! aws s3api head-bucket --bucket "$target_bucket" 2> /dev/null; then
        log_error "S3 bucket does not exist or is not accessible: $target_bucket"
        return 1
    fi
    
    # Create backup of existing content
    local backup_prefix="backups/${TIMESTAMP}"
    if [[ "$DRY_RUN" == "false" ]]; then
        log_info "Creating backup at s3://$target_bucket/$backup_prefix"
        aws s3 sync "s3://$target_bucket/$target_prefix" "s3://$target_bucket/$backup_prefix" \
            --delete \
            --only-show-errors
    fi
    
    # Sync files to S3
    local sync_cmd="aws s3 sync \"$source_path\" \"s3://$target_bucket/$target_prefix\" --delete --exclude '*.git/*' --exclude '.env*' --exclude '*.log'"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_warn "DRY RUN: Would execute: $sync_cmd"
        eval "$sync_cmd --dryrun"
    else
        eval "$sync_cmd"
        log_info "S3 deployment completed successfully"
    fi
}

# CloudFormation deployment function
deploy_cloudformation() {
    local template_file="$1"
    local stack_name="$2"
    local parameters_file="${3:-}"
    
    if [[ ! -f "$template_file" ]]; then
        log_error "CloudFormation template not found: $template_file"
        return 1
    fi
    
    log_info "Deploying CloudFormation stack: $stack_name"
    
    # Validate template
    if ! aws cloudformation validate-template --template-body "file://$template_file" > /dev/null; then
        log_error "CloudFormation template validation failed"
        return 1
    fi
    
    # Build parameters
    local params=""
    if [[ -n "$parameters_file" && -f "$parameters_file" ]]; then
        params="--parameters file://$parameters_file"
    fi
    
    # Check if stack exists
    if aws cloudformation describe-stacks --stack-name "$stack_name" &> /dev/null; then
        local action="update"
        local wait_condition="stack-update-complete"
    else
        local action="create"
        local wait_condition="stack-create-complete"
    fi
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_warn "DRY RUN: Would $action stack $stack_name"
        aws cloudformation deploy \
            --template-file "$template_file" \
            --stack-name "$stack_name" \
            $params \
            --no-execute-changeset
    else
        aws cloudformation deploy \
            --template-file "$template_file" \
            --stack-name "$stack_name" \
            $params \
            --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM
        
        log_info "Waiting for stack $action to complete..."
        aws cloudformation wait "$wait_condition" --stack-name "$stack_name"
        log_info "CloudFormation deployment completed successfully"
    fi
}

# ECS deployment function
deploy_ecs() {
    local cluster="$1"
    local service="$2"
    local task_definition="${3:-}"
    
    log_info "Deploying to ECS cluster: $cluster, service: $service"
    
    # Verify cluster exists
    if ! aws ecs describe-clusters --clusters "$cluster" | jq -e '.clusters[0].status == "ACTIVE"' > /dev/null; then
        log_error "ECS cluster not found or not active: $cluster"
        return 1
    fi
    
    # Register new task definition if provided
    if [[ -n "$task_definition" && -f "$task_definition" ]]; then
        log_info "Registering new task definition"
        
        if [[ "$DRY_RUN" == "true" ]]; then
            log_warn "DRY RUN: Would register task definition from $task_definition"
        else
            TASK_ARN=$(aws ecs register-task-definition \
                --cli-input-json "file://$task_definition" \
                --query 'taskDefinition.taskDefinitionArn' \
                --output text)
            log_info "Registered task definition: $TASK_ARN"
        fi
    fi
    
    # Force new deployment
    if [[ "$DRY_RUN" == "true" ]]; then
        log_warn "DRY RUN: Would update service $service"
    else
        aws ecs update-service \
            --cluster "$cluster" \
            --service "$service" \
            --force-new-deployment \
            --query 'service.taskDefinition' \
            --output text
        
        log_info "Waiting for service to stabilize..."
        aws ecs wait services-stable --cluster "$cluster" --services "$service"
        log_info "ECS deployment completed successfully"
    fi
}

# Lambda deployment function
deploy_lambda() {
    local function_name="$1"
    local zip_file="$2"
    local handler="${3:-index.handler}"
    local runtime="${4:-python3.9}"
    
    if [[ ! -f "$zip_file" ]]; then
        log_error "Lambda deployment package not found: $zip_file"
        return 1
    fi
    
    log_info "Deploying Lambda function: $function_name"
    
    # Check if function exists
    if aws lambda get-function --function-name "$function_name" &> /dev/null; then
        # Update existing function
        if [[ "$DRY_RUN" == "true" ]]; then
            log_warn "DRY RUN: Would update Lambda function $function_name"
        else
            aws lambda update-function-code \
                --function-name "$function_name" \
                --zip-file "fileb://$zip_file" \
                --publish
            
            # Wait for update to complete
            aws lambda wait function-updated --function-name "$function_name"
            log_info "Lambda function updated successfully"
        fi
    else
        log_error "Lambda function does not exist: $function_name"
        log_info "Please create the function first or use CloudFormation/Terraform"
        return 1
    fi
}

# Main deployment orchestration
main() {
    log_info "Starting AWS deployment script"
    log_info "Environment: $DEPLOYMENT_ENV"
    log_info "Dry run: $DRY_RUN"
    
    # Check dependencies
    check_dependencies
    
    # Validate credentials
    validate_aws_credentials
    
    # Parse command line arguments
    case "${1:-}" in
        s3)
            if [[ -z "$S3_BUCKET" ]]; then
                log_error "S3_BUCKET environment variable is required"
                exit 1
            fi
            deploy_to_s3 "${2:-./dist}" "$S3_BUCKET" "${3:-}"
            ;;
        cloudformation|cf)
            if [[ -z "$CLOUDFORMATION_STACK" ]]; then
                log_error "CLOUDFORMATION_STACK environment variable is required"
                exit 1
            fi
            deploy_cloudformation "${2:-./cloudformation/template.yaml}" "$CLOUDFORMATION_STACK" "${3:-}"
            ;;
        ecs)
            if [[ -z "$ECS_CLUSTER" || -z "$ECS_SERVICE" ]]; then
                log_error "ECS_CLUSTER and ECS_SERVICE environment variables are required"
                exit 1
            fi
            deploy_ecs "$ECS_CLUSTER" "$ECS_SERVICE" "${2:-}"
            ;;
        lambda)
            if [[ -z "$LAMBDA_FUNCTION" ]]; then
                log_error "LAMBDA_FUNCTION environment variable is required"
                exit 1
            fi
            deploy_lambda "$LAMBDA_FUNCTION" "${2:-./lambda.zip}" "${3:-}" "${4:-}"
            ;;
        *)
            cat << EOF
Usage: $SCRIPT_NAME [command] [options]

Commands:
    s3 [source_path] [target_prefix]          Deploy to S3 bucket
    cloudformation [template] [parameters]     Deploy CloudFormation stack
    ecs [task_definition]                     Deploy to ECS service
    lambda [zip_file] [handler] [runtime]     Deploy Lambda function

Environment Variables:
    AWS_REGION              AWS region (default: us-east-1)
    AWS_PROFILE             AWS profile for local development
    AWS_ACCESS_KEY_ID       AWS access key (for CI/CD)
    AWS_SECRET_ACCESS_KEY   AWS secret key (for CI/CD)
    DEPLOYMENT_ENV          Deployment environment (default: development)
    DRY_RUN                 Perform dry run only (default: false)
    
    S3_BUCKET              S3 bucket name (for s3 command)
    CLOUDFORMATION_STACK   CloudFormation stack name
    ECS_CLUSTER            ECS cluster name
    ECS_SERVICE            ECS service name
    LAMBDA_FUNCTION        Lambda function name

Examples:
    # Deploy to S3
    S3_BUCKET=my-bucket $SCRIPT_NAME s3 ./dist
    
    # Deploy CloudFormation stack
    CLOUDFORMATION_STACK=my-stack $SCRIPT_NAME cloudformation template.yaml params.json
    
    # Deploy to ECS
    ECS_CLUSTER=my-cluster ECS_SERVICE=my-service $SCRIPT_NAME ecs
    
    # Deploy Lambda function
    LAMBDA_FUNCTION=my-function $SCRIPT_NAME lambda function.zip
    
    # Dry run mode
    DRY_RUN=true S3_BUCKET=my-bucket $SCRIPT_NAME s3 ./dist
EOF
            exit 0
            ;;
    esac
    
    log_info "Deployment completed successfully"
}

# Execute main function
main "$@"