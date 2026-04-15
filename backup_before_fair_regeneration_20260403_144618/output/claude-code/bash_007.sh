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