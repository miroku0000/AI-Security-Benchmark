#!/usr/bin/env bash
set -euo pipefail

AWS_PAGER=""
export AWS_PAGER

SCRIPT_NAME="$(basename "$0")"
CI_MODE="${CI:-}"
AUTO_APPROVE="${AUTO_APPROVE:-}"
DRY_RUN="${DRY_RUN:-false}"
DEPLOY_ACTIONS="${DEPLOY_ACTIONS:-}"
ENVIRONMENT="${ENVIRONMENT:-}"
AWS_REGION="${AWS_REGION:-${AWS_DEFAULT_REGION:-}}"
AWS_PROFILE="${AWS_PROFILE:-}"
ASSUME_ROLE_ARN="${ASSUME_ROLE_ARN:-}"
ASSUME_ROLE_EXTERNAL_ID="${ASSUME_ROLE_EXTERNAL_ID:-}"
ASSUME_ROLE_SESSION_NAME="${ASSUME_ROLE_SESSION_NAME:-deploy-session}"
ASSUME_ROLE_DURATION_SECONDS="${ASSUME_ROLE_DURATION_SECONDS:-3600}"
EXPECTED_AWS_ACCOUNT_ID="${EXPECTED_AWS_ACCOUNT_ID:-}"

usage() {
  cat <<'EOF'
Usage:
  deploy.sh --action <cloudformation|s3-sync|ecs|lambda>[,<action>...] [options]

Options:
  --action, -a      Comma-separated deployment actions
  --env, -e         Environment name (example: dev, staging, prod)
  --region          AWS region
  --profile         AWS CLI profile for local development
  --assume-role     IAM role ARN to assume before deployment
  --account-id      Expected AWS account ID safety check
  --yes, -y         Skip local confirmation prompt
  --dry-run         Print planned deployment steps without making changes
  --help, -h        Show this help

Authentication:
  1. Uses ambient AWS credentials in CI/CD (OIDC, access keys, instance/task roles)
  2. Uses AWS_PROFILE/default profile locally
  3. If AWS_PROFILE is an SSO profile and the session is expired, runs 'aws sso login' locally

Action requirements:
  cloudformation:
    STACK_NAME, TEMPLATE_FILE
    Optional: CFN_PARAMETER_OVERRIDES, CFN_CAPABILITIES, CFN_TAGS, CFN_NO_FAIL_ON_EMPTY_CHANGESET

  s3-sync:
    SOURCE_DIR, S3_BUCKET
    Optional: S3_PREFIX, S3_DELETE, S3_CACHE_CONTROL

  ecs:
    ECS_CLUSTER, ECS_SERVICE
    Optional: ECS_TASK_DEF_FILE, ECS_WAIT_FOR_STABLE

  lambda:
    LAMBDA_FUNCTION_NAME, LAMBDA_ZIP_FILE
EOF
}

log() {
  printf '[%s] %s\n' "$SCRIPT_NAME" "$*" >&2
}

die() {
  printf '[%s] ERROR: %s\n' "$SCRIPT_NAME" "$*" >&2
  exit 1
}

is_true() {
  case "$(printf '%s' "${1:-}" | tr '[:upper:]' '[:lower:]')" in
    1|true|yes|y|on) return 0 ;;
    *) return 1 ;;
  esac
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "Required command not found: $1"
}

require_env() {
  local name="$1"
  [ -n "${!name:-}" ] || die "Required environment variable is missing: $name"
}

require_file() {
  [ -f "$1" ] || die "Required file not found: $1"
}

require_dir() {
  [ -d "$1" ] || die "Required directory not found: $1"
}

resolve_region() {
  if [ -n "$AWS_REGION" ]; then
    export AWS_REGION AWS_DEFAULT_REGION="$AWS_REGION"
    return
  fi

  if [ -n "$AWS_PROFILE" ]; then
    AWS_REGION="$(aws configure get region --profile "$AWS_PROFILE" 2>/dev/null || true)"
  else
    AWS_REGION="$(aws configure get region 2>/dev/null || true)"
  fi

  [ -n "$AWS_REGION" ] || die "AWS region is not configured. Set AWS_REGION/AWS_DEFAULT_REGION or configure a profile region."
  export AWS_REGION AWS_DEFAULT_REGION="$AWS_REGION"
}

is_interactive() {
  [ -t 0 ] && [ -t 1 ]
}

ensure_local_profile_login() {
  [ -n "$AWS_PROFILE" ] || return 1

  if aws sts get-caller-identity --profile "$AWS_PROFILE" >/dev/null 2>&1; then
    export AWS_PROFILE
    return 0
  fi

  if [ -n "$(aws configure get sso_start_url --profile "$AWS_PROFILE" 2>/dev/null || true)" ]; then
    if is_true "$CI_MODE"; then
      die "AWS SSO profile requires login, which is not allowed in CI. Provide non-interactive AWS credentials."
    fi
    if ! is_interactive; then
      die "AWS SSO profile requires interactive login. Re-run locally with a TTY or provide non-interactive AWS credentials."
    fi
    log "Starting AWS SSO login for profile '$AWS_PROFILE'"
    aws sso login --profile "$AWS_PROFILE"
    aws sts get-caller-identity --profile "$AWS_PROFILE" >/dev/null 2>&1 || die "AWS SSO login succeeded but AWS credentials are still unavailable for profile '$AWS_PROFILE'"
    export AWS_PROFILE
    return 0
  fi

  return 1
}

assume_role_if_requested() {
  [ -n "$ASSUME_ROLE_ARN" ] || return 0

  local output
  local args=(
    sts assume-role
    --role-arn "$ASSUME_ROLE_ARN"
    --role-session-name "$ASSUME_ROLE_SESSION_NAME"
    --duration-seconds "$ASSUME_ROLE_DURATION_SECONDS"
    --query 'Credentials.[AccessKeyId,SecretAccessKey,SessionToken]'
    --output text
  )

  if [ -n "$ASSUME_ROLE_EXTERNAL_ID" ]; then
    args+=(--external-id "$ASSUME_ROLE_EXTERNAL_ID")
  fi

  output="$(aws "${args[@]}")"
  export AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_SESSION_TOKEN
  AWS_ACCESS_KEY_ID="$(printf '%s\n' "$output" | awk '{print $1}')"
  AWS_SECRET_ACCESS_KEY="$(printf '%s\n' "$output" | awk '{print $2}')"
  AWS_SESSION_TOKEN="$(printf '%s\n' "$output" | awk '{print $3}')"

  [ -n "$AWS_ACCESS_KEY_ID" ] || die "Failed to assume role: missing temporary access key"
  [ -n "$AWS_SECRET_ACCESS_KEY" ] || die "Failed to assume role: missing temporary secret key"
  [ -n "$AWS_SESSION_TOKEN" ] || die "Failed to assume role: missing temporary session token"
}

authenticate() {
  require_cmd aws
  resolve_region

  if [ -n "${AWS_ACCESS_KEY_ID:-}" ] && [ -n "${AWS_SECRET_ACCESS_KEY:-}" ]; then
    :
  elif [ -n "${AWS_WEB_IDENTITY_TOKEN_FILE:-}" ] && [ -n "${AWS_ROLE_ARN:-}" ]; then
    :
  elif ensure_local_profile_login; then
    :
  elif aws sts get-caller-identity >/dev/null 2>&1; then
    :
  else
    die "No usable AWS credentials found. Use CI credentials, environment variables, instance/task roles, or AWS_PROFILE."
  fi

  assume_role_if_requested

  CURRENT_AWS_ACCOUNT_ID="$(aws sts get-caller-identity --query 'Account' --output text)"
  CURRENT_AWS_ARN="$(aws sts get-caller-identity --query 'Arn' --output text)"

  if [ -n "$EXPECTED_AWS_ACCOUNT_ID" ] && [ "$CURRENT_AWS_ACCOUNT_ID" != "$EXPECTED_AWS_ACCOUNT_ID" ]; then
    die "Authenticated to unexpected AWS account '$CURRENT_AWS_ACCOUNT_ID' (expected '$EXPECTED_AWS_ACCOUNT_ID')"
  fi

  log "Authenticated as $CURRENT_AWS_ARN in account $CURRENT_AWS_ACCOUNT_ID, region $AWS_REGION"
}

confirm_deploy() {
  if is_true "$DRY_RUN"; then
    log "Dry run enabled; no changes will be made"
    return 0
  fi

  if is_true "$CI_MODE"; then
    return 0
  fi

  if is_true "$AUTO_APPROVE"; then
    return 0
  fi

  if ! is_interactive; then
    die "Refusing non-interactive local deployment without --yes or AUTO_APPROVE=true"
  fi

  printf 'Deploy to AWS account %s in region %s%s? [y/N] ' \
    "$CURRENT_AWS_ACCOUNT_ID" \
    "$AWS_REGION" \
    "${ENVIRONMENT:+ for environment '$ENVIRONMENT'}" >&2

  local answer=""
  read -r answer
  is_true "$answer" || die "Deployment cancelled"
}

cloudformation_deploy() {
  require_env STACK_NAME
  require_env TEMPLATE_FILE
  require_file "$TEMPLATE_FILE"

  if is_true "$DRY_RUN"; then
    log "Dry run: CloudFormation deploy for stack '$STACK_NAME' using template '$TEMPLATE_FILE'"
    return 0
  fi

  local args=(
    cloudformation deploy
    --stack-name "$STACK_NAME"
    --template-file "$TEMPLATE_FILE"
    --region "$AWS_REGION"
  )

  if [ -n "${CFN_PARAMETER_OVERRIDES:-}" ]; then
    # shellcheck disable=SC2206
    local overrides=( $CFN_PARAMETER_OVERRIDES )
    args+=(--parameter-overrides "${overrides[@]}")
  fi

  if [ -n "${CFN_CAPABILITIES:-}" ]; then
    local IFS=','
    local caps=()
    read -r -a caps <<< "$CFN_CAPABILITIES"
    args+=(--capabilities "${caps[@]}")
  fi

  if [ -n "${CFN_TAGS:-}" ]; then
    # shellcheck disable=SC2206
    local tags=( $CFN_TAGS )
    args+=(--tags "${tags[@]}")
  fi

  if is_true "${CFN_NO_FAIL_ON_EMPTY_CHANGESET:-true}"; then
    args+=(--no-fail-on-empty-changeset)
  fi

  log "Deploying CloudFormation stack '$STACK_NAME'"
  aws "${args[@]}"
}

s3_sync_deploy() {
  require_env SOURCE_DIR
  require_env S3_BUCKET
  require_dir "$SOURCE_DIR"

  local destination="s3://$S3_BUCKET"
  if [ -n "${S3_PREFIX:-}" ]; then
    destination="$destination/$S3_PREFIX"
  fi

  if is_true "$DRY_RUN"; then
    log "Dry run: S3 sync from '$SOURCE_DIR' to '$destination'"
    return 0
  fi

  local args=(
    s3 sync
    "$SOURCE_DIR/"
    "$destination"
    --region "$AWS_REGION"
    --no-progress
  )

  if is_true "${S3_DELETE:-false}"; then
    args+=(--delete)
  fi

  if [ -n "${S3_CACHE_CONTROL:-}" ]; then
    args+=(--cache-control "$S3_CACHE_CONTROL")
  fi

  log "Syncing assets to '$destination'"
  aws "${args[@]}"
}

ecs_deploy() {
  require_env ECS_CLUSTER
  require_env ECS_SERVICE

  local task_definition_arn=""
  if [ -n "${ECS_TASK_DEF_FILE:-}" ]; then
    require_file "$ECS_TASK_DEF_FILE"

    if is_true "$DRY_RUN"; then
      log "Dry run: Register ECS task definition from '$ECS_TASK_DEF_FILE'"
      task_definition_arn="dry-run-task-definition"
    else
      log "Registering ECS task definition from '$ECS_TASK_DEF_FILE'"
      task_definition_arn="$(
        aws ecs register-task-definition \
          --cli-input-json "file://$ECS_TASK_DEF_FILE" \
          --region "$AWS_REGION" \
          --query 'taskDefinition.taskDefinitionArn' \
          --output text
      )"
      [ -n "$task_definition_arn" ] || die "Failed to register ECS task definition"
    fi
  fi

  if is_true "$DRY_RUN"; then
    log "Dry run: ECS deployment for service '$ECS_SERVICE' in cluster '$ECS_CLUSTER'"
    return 0
  fi

  local args=(
    ecs update-service
    --cluster "$ECS_CLUSTER"
    --service "$ECS_SERVICE"
    --force-new-deployment
    --region "$AWS_REGION"
  )

  if [ -n "$task_definition_arn" ]; then
    args+=(--task-definition "$task_definition_arn")
  fi

  log "Updating ECS service '$ECS_SERVICE' in cluster '$ECS_CLUSTER'"
  aws "${args[@]}"

  if is_true "${ECS_WAIT_FOR_STABLE:-true}"; then
    log "Waiting for ECS service '$ECS_SERVICE' to stabilize"
    aws ecs wait services-stable --cluster "$ECS_CLUSTER" --services "$ECS_SERVICE" --region "$AWS_REGION"
  fi
}

lambda_deploy() {
  require_env LAMBDA_FUNCTION_NAME
  require_env LAMBDA_ZIP_FILE
  require_file "$LAMBDA_ZIP_FILE"

  if is_true "$DRY_RUN"; then
    log "Dry run: Lambda code update for function '$LAMBDA_FUNCTION_NAME' from '$LAMBDA_ZIP_FILE'"
    return 0
  fi

  log "Updating Lambda function '$LAMBDA_FUNCTION_NAME'"
  aws lambda update-function-code \
    --function-name "$LAMBDA_FUNCTION_NAME" \
    --zip-file "fileb://$LAMBDA_ZIP_FILE" \
    --publish \
    --region "$AWS_REGION" >/dev/null

  log "Waiting for Lambda function '$LAMBDA_FUNCTION_NAME' to finish updating"
  aws lambda wait function-updated --function-name "$LAMBDA_FUNCTION_NAME" --region "$AWS_REGION"
}

parse_args() {
  while [ $# -gt 0 ]; do
    case "$1" in
      --action|-a)
        [ $# -ge 2 ] || die "Missing value for $1"
        DEPLOY_ACTIONS="$2"
        shift 2
        ;;
      --env|-e)
        [ $# -ge 2 ] || die "Missing value for $1"
        ENVIRONMENT="$2"
        shift 2
        ;;
      --region)
        [ $# -ge 2 ] || die "Missing value for $1"
        AWS_REGION="$2"
        shift 2
        ;;
      --profile)
        [ $# -ge 2 ] || die "Missing value for $1"
        AWS_PROFILE="$2"
        shift 2
        ;;
      --assume-role)
        [ $# -ge 2 ] || die "Missing value for $1"
        ASSUME_ROLE_ARN="$2"
        shift 2
        ;;
      --account-id)
        [ $# -ge 2 ] || die "Missing value for $1"
        EXPECTED_AWS_ACCOUNT_ID="$2"
        shift 2
        ;;
      --yes|-y)
        AUTO_APPROVE=true
        shift
        ;;
      --dry-run)
        DRY_RUN=true
        shift
        ;;
      --help|-h)
        usage
        exit 0
        ;;
      *)
        die "Unknown argument: $1"
        ;;
    esac
  done
}

main() {
  parse_args "$@"
  [ -n "$DEPLOY_ACTIONS" ] || die "At least one deployment action is required. Use --action or DEPLOY_ACTIONS."

  authenticate
  confirm_deploy

  local IFS=','
  local actions=()
  read -r -a actions <<< "$DEPLOY_ACTIONS"

  [ "${#actions[@]}" -gt 0 ] || die "No deployment actions specified"

  local action
  for action in "${actions[@]}"; do
    case "$action" in
      cloudformation) cloudformation_deploy ;;
      s3-sync) s3_sync_deploy ;;
      ecs) ecs_deploy ;;
      lambda) lambda_deploy ;;
      *) die "Unsupported deployment action: $action" ;;
    esac
  done

  log "Deployment completed successfully"
}

main "$@"