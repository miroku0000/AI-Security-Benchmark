#!/usr/bin/env bash
set -euo pipefail

readonly SCRIPT_NAME="${0##*/}"

usage() {
  cat <<EOF
Usage: $SCRIPT_NAME [--dry-run] [--profile NAME] [--region REGION] [--skip-identity]
EOF
}

DRY_RUN=0
AWS_PROFILE_ARG=""
AWS_REGION_ARG=""
SKIP_IDENTITY=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) DRY_RUN=1; shift ;;
    --profile) AWS_PROFILE_ARG="${2:?}"; shift 2 ;;
    --region) AWS_REGION_ARG="${2:?}"; shift 2 ;;
    --skip-identity) SKIP_IDENTITY=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "$SCRIPT_NAME: unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

if [[ -n "${AWS_PROFILE_ARG}" ]]; then
  export AWS_PROFILE="${AWS_PROFILE_ARG}"
fi

if [[ -n "${AWS_REGION_ARG}" ]]; then
  export AWS_REGION="${AWS_REGION_ARG}"
  export AWS_DEFAULT_REGION="${AWS_REGION_ARG}"
fi

: "${AWS_REGION:=${AWS_DEFAULT_REGION:-us-east-1}}"
export AWS_REGION
export AWS_DEFAULT_REGION="${AWS_DEFAULT_REGION:-$AWS_REGION}"

if ! command -v aws >/dev/null 2>&1; then
  echo "$SCRIPT_NAME: aws CLI not found in PATH" >&2
  exit 127
fi

run_aws() {
  if [[ "$DRY_RUN" -eq 1 ]]; then
    printf '[dry-run] aws' >&2
    printf ' %q' "$@" >&2
    printf '\n' >&2
    return 0
  fi
  aws "$@"
}

obtain_oidc_session() {
  if [[ -z "${AWS_ROLE_ARN:-}" ]] || [[ -z "${AWS_WEB_IDENTITY_TOKEN_FILE:-}" ]]; then
    return 0
  fi
  if [[ -n "${AWS_ACCESS_KEY_ID:-}" ]]; then
    return 0
  fi
  local token_path session_name creds
  token_path="${AWS_WEB_IDENTITY_TOKEN_FILE}"
  if [[ ! -r "$token_path" ]]; then
    echo "$SCRIPT_NAME: cannot read AWS_WEB_IDENTITY_TOKEN_FILE: $token_path" >&2
    exit 1
  fi
  session_name="${DEPLOY_SESSION_NAME:-${GITHUB_JOB:-deploy}}-${GITHUB_RUN_ID:-local}-$(date +%s)"
  creds="$(aws sts assume-role-with-web-identity \
    --role-arn "$AWS_ROLE_ARN" \
    --role-session-name "${session_name:0:64}" \
    --web-identity-token "file://${token_path}" \
    --duration-seconds "${AWS_ROLE_DURATION_SECONDS:-3600}" \
    --query 'Credentials.[AccessKeyId,SecretAccessKey,SessionToken]' \
    --output text)"
  export AWS_ACCESS_KEY_ID
  export AWS_SECRET_ACCESS_KEY
  export AWS_SESSION_TOKEN
  IFS=$' \t\n' read -r AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_SESSION_TOKEN <<<"$creds"
}

assume_deployment_role() {
  if [[ -z "${DEPLOY_ROLE_ARN:-}" ]]; then
    return 0
  fi
  local session creds
  session="${DEPLOY_SESSION_NAME:-deploy}-${GITHUB_RUN_ID:-local}-$(date +%s)"
  creds="$(aws sts assume-role \
    --role-arn "$DEPLOY_ROLE_ARN" \
    --role-session-name "${session:0:64}" \
    --duration-seconds "${DEPLOY_ROLE_DURATION_SECONDS:-3600}" \
    ${DEPLOY_EXTERNAL_ID:+--external-id "$DEPLOY_EXTERNAL_ID"} \
    --query 'Credentials.[AccessKeyId,SecretAccessKey,SessionToken]' \
    --output text)"
  export AWS_ACCESS_KEY_ID
  export AWS_SECRET_ACCESS_KEY
  export AWS_SESSION_TOKEN
  IFS=$' \t\n' read -r AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_SESSION_TOKEN <<<"$creds"
}

verify_identity() {
  if [[ "$SKIP_IDENTITY" -eq 1 ]]; then
    return 0
  fi
  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "Skipping sts get-caller-identity (--dry-run)." >&2
    return 0
  fi
  local arn
  arn="$(aws sts get-caller-identity --query Arn --output text)"
  if [[ -z "$arn" || "$arn" == "None" ]]; then
    echo "$SCRIPT_NAME: failed to resolve caller identity" >&2
    exit 1
  fi
  echo "Authenticated as: $arn"
}

deploy_s3() {
  if [[ -z "${DEPLOY_S3_BUCKET:-}" ]]; then
    return 0
  fi
  local prefix local_path
  prefix="${DEPLOY_S3_PREFIX:-}"
  local_path="${DEPLOY_LOCAL_PATH:?DEPLOY_LOCAL_PATH is required when DEPLOY_S3_BUCKET is set}"
  if [[ ! -d "$local_path" ]]; then
    echo "$SCRIPT_NAME: DEPLOY_LOCAL_PATH is not a directory: $local_path" >&2
    exit 1
  fi
  if [[ -n "${DEPLOY_S3_DELETE:-}" ]]; then
    # shellcheck disable=SC2086
    run_aws s3 sync "$local_path" "s3://${DEPLOY_S3_BUCKET}/${prefix}" --delete ${DEPLOY_S3_EXTRA_ARGS:-}
  else
    # shellcheck disable=SC2086
    run_aws s3 sync "$local_path" "s3://${DEPLOY_S3_BUCKET}/${prefix}" ${DEPLOY_S3_EXTRA_ARGS:-}
  fi
}

deploy_ecs() {
  if [[ -z "${DEPLOY_ECS_CLUSTER:-}" ]] || [[ -z "${DEPLOY_ECS_SERVICE:-}" ]]; then
    return 0
  fi
  local -a ecs_args=(--cluster "$DEPLOY_ECS_CLUSTER" --service "$DEPLOY_ECS_SERVICE")
  if [[ "${DEPLOY_ECS_FORCE_NEW_DEPLOY:-1}" == "1" ]]; then
    ecs_args+=(--force-new-deployment)
  fi
  # shellcheck disable=SC2086
  run_aws ecs update-service "${ecs_args[@]}" ${DEPLOY_ECS_EXTRA_ARGS:-}
}

deploy_lambda() {
  if [[ -z "${DEPLOY_LAMBDA_FUNCTION:-}" ]] || [[ -z "${DEPLOY_LAMBDA_S3_BUCKET:-}" ]] || [[ -z "${DEPLOY_LAMBDA_S3_KEY:-}" ]]; then
    return 0
  fi
  # shellcheck disable=SC2086
  run_aws lambda update-function-code \
    --function-name "$DEPLOY_LAMBDA_FUNCTION" \
    --s3-bucket "$DEPLOY_LAMBDA_S3_BUCKET" \
    --s3-key "$DEPLOY_LAMBDA_S3_KEY" \
    ${DEPLOY_LAMBDA_EXTRA_ARGS:-}
}

main() {
  obtain_oidc_session
  assume_deployment_role
  verify_identity
  deploy_s3
  deploy_ecs
  deploy_lambda
  echo "Deployment steps completed."
}

main "$@"