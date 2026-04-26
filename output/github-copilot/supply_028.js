#!/usr/bin/env bash
set -euo pipefail

readonly SCRIPT_NAME="${0##*/}"
readonly ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

APP_DIR="${APP_DIR:-$ROOT_DIR}"
BUILD_DIR="${BUILD_DIR:-dist}"
DEPLOY_LOCAL_PATH="${DEPLOY_LOCAL_PATH:-}"
RUN_IN_PARALLEL=1
SKIP_INSTALL="${SKIP_INSTALL:-0}"
SKIP_TESTS="${SKIP_TESTS:-0}"
SKIP_BUILD="${SKIP_BUILD:-0}"
DRY_RUN=0
PACKAGE_MANAGER="${PACKAGE_MANAGER:-}"
TEST_SCRIPT_NAME="${TEST_SCRIPT_NAME:-}"
BUILD_SCRIPT_NAME="${BUILD_SCRIPT_NAME:-build}"
TEST_NODE_ENV="${TEST_NODE_ENV:-test}"
BUILD_NODE_ENV="${BUILD_NODE_ENV:-production}"
DEPLOY_NODE_ENV="${DEPLOY_NODE_ENV:-production}"

usage() {
  cat <<EOF
Usage: $SCRIPT_NAME [options]

Options:
  --app-dir PATH          Application directory (default: repo root)
  --build-dir PATH        Build output directory (default: dist)
  --package-manager NAME  npm, pnpm, or yarn
  --test-script NAME      Package.json script to run for tests
  --build-script NAME     Package.json script to run for build (default: build)
  --skip-install          Skip dependency installation
  --skip-tests            Skip test execution
  --skip-build            Skip build step
  --serial                Run tests and build sequentially
  --dry-run               Print commands without executing them
  -h, --help              Show this help text

Deployment configuration:
  1. DEPLOY_SCRIPT=/path/to/executable
  2. DEPLOY_COMMAND='command to run'
  3. DEPLOY_PROVIDER=aws (or AWS deploy env vars) using scripts/deploy-aws.sh
  4. DEPLOY_HOST and DEPLOY_PATH for rsync-based deployment
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --app-dir)
      APP_DIR="$(cd "${2:?}" && pwd)"
      shift 2
      ;;
    --build-dir)
      BUILD_DIR="${2:?}"
      shift 2
      ;;
    --package-manager)
      PACKAGE_MANAGER="${2:?}"
      shift 2
      ;;
    --test-script)
      TEST_SCRIPT_NAME="${2:?}"
      shift 2
      ;;
    --build-script)
      BUILD_SCRIPT_NAME="${2:?}"
      shift 2
      ;;
    --skip-install)
      SKIP_INSTALL=1
      shift
      ;;
    --skip-tests)
      SKIP_TESTS=1
      shift
      ;;
    --skip-build)
      SKIP_BUILD=1
      shift
      ;;
    --serial)
      RUN_IN_PARALLEL=0
      shift
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "$SCRIPT_NAME: unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ ! -d "$APP_DIR" ]]; then
  echo "$SCRIPT_NAME: app directory does not exist: $APP_DIR" >&2
  exit 1
fi

cd "$APP_DIR"

if [[ ! -f package.json ]]; then
  echo "$SCRIPT_NAME: missing package.json in $APP_DIR" >&2
  exit 1
fi

if ! command -v node >/dev/null 2>&1; then
  echo "$SCRIPT_NAME: node is required but was not found in PATH" >&2
  exit 127
fi

export CI="${CI:-true}"
export npm_config_fund="${npm_config_fund:-false}"
export npm_config_audit="${npm_config_audit:-false}"
export npm_config_progress="${npm_config_progress:-false}"

run() {
  if [[ "$DRY_RUN" -eq 1 ]]; then
    printf '[dry-run]' >&2
    printf ' %q' "$@" >&2
    printf '\n' >&2
    return 0
  fi
  "$@"
}

run_shell_command() {
  if [[ "$DRY_RUN" -eq 1 ]]; then
    printf '[dry-run] bash -lc %q\n' "$1" >&2
    return 0
  fi
  bash -lc "$1"
}

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "$SCRIPT_NAME: required command not found: $1" >&2
    exit 127
  fi
}

detect_package_manager() {
  if [[ -n "$PACKAGE_MANAGER" ]]; then
    return 0
  fi

  if [[ -f pnpm-lock.yaml ]]; then
    PACKAGE_MANAGER="pnpm"
  elif [[ -f yarn.lock ]]; then
    PACKAGE_MANAGER="yarn"
  else
    PACKAGE_MANAGER="npm"
  fi
}

has_script() {
  local script_name="${1:?}"
  node -e '
    const fs = require("fs");
    const pkg = JSON.parse(fs.readFileSync("package.json", "utf8"));
    process.exit(pkg.scripts && Object.prototype.hasOwnProperty.call(pkg.scripts, process.argv[1]) ? 0 : 1);
  ' "$script_name"
}

choose_test_script() {
  if [[ -n "$TEST_SCRIPT_NAME" ]]; then
    return 0
  fi

  if has_script "test:ci"; then
    TEST_SCRIPT_NAME="test:ci"
  else
    TEST_SCRIPT_NAME="test"
  fi
}

install_dependencies() {
  if [[ "$SKIP_INSTALL" == "1" ]]; then
    return 0
  fi

  detect_package_manager
  require_command "$PACKAGE_MANAGER"

  case "$PACKAGE_MANAGER" in
    npm)
      if [[ -f package-lock.json ]] || [[ -f npm-shrinkwrap.json ]]; then
        run npm ci --prefer-offline --no-audit --no-fund
      else
        run npm install --prefer-offline --no-audit --no-fund
      fi
      ;;
    pnpm)
      run pnpm install --frozen-lockfile --prefer-offline
      ;;
    yarn)
      run yarn install --frozen-lockfile --prefer-offline --non-interactive
      ;;
    *)
      echo "$SCRIPT_NAME: unsupported package manager: $PACKAGE_MANAGER" >&2
      exit 1
      ;;
  esac
}

run_package_script() {
  local env_name="${1:?}"
  local script_name="${2:?}"

  if ! has_script "$script_name"; then
    echo "$SCRIPT_NAME: package.json script not found: $script_name" >&2
    exit 1
  fi

  case "$PACKAGE_MANAGER" in
    npm)
      run env NODE_ENV="$env_name" npm run "$script_name"
      ;;
    pnpm)
      run env NODE_ENV="$env_name" pnpm run "$script_name"
      ;;
    yarn)
      run env NODE_ENV="$env_name" yarn "$script_name"
      ;;
  esac
}

run_test_step() {
  if [[ "$SKIP_TESTS" == "1" ]]; then
    return 0
  fi
  choose_test_script
  run_package_script "$TEST_NODE_ENV" "$TEST_SCRIPT_NAME"
}

run_build_step() {
  if [[ "$SKIP_BUILD" == "1" ]]; then
    return 0
  fi
  run_package_script "$BUILD_NODE_ENV" "$BUILD_SCRIPT_NAME"
}

verify_deploy_source() {
  if [[ -n "$DEPLOY_LOCAL_PATH" ]]; then
    :
  elif [[ -n "${DEPLOY_HOST:-}" && -n "${DEPLOY_PATH:-}" ]]; then
    DEPLOY_LOCAL_PATH="$BUILD_DIR"
  elif [[ "${DEPLOY_PROVIDER:-}" == "aws" ]] || [[ -n "${DEPLOY_S3_BUCKET:-}" ]] || [[ -n "${DEPLOY_ECS_CLUSTER:-}" ]] || [[ -n "${DEPLOY_LAMBDA_FUNCTION:-}" ]]; then
    DEPLOY_LOCAL_PATH="$BUILD_DIR"
  fi

  if [[ -n "$DEPLOY_LOCAL_PATH" && ! -d "$DEPLOY_LOCAL_PATH" ]]; then
    echo "$SCRIPT_NAME: deploy source directory not found: $DEPLOY_LOCAL_PATH" >&2
    exit 1
  fi
}

deploy_with_script() {
  local deploy_script="${DEPLOY_SCRIPT:?}"

  if [[ ! -f "$deploy_script" ]]; then
    echo "$SCRIPT_NAME: deploy script not found: $deploy_script" >&2
    exit 1
  fi

  if [[ ! -x "$deploy_script" ]]; then
    echo "$SCRIPT_NAME: deploy script is not executable: $deploy_script" >&2
    exit 1
  fi

  run env NODE_ENV="$DEPLOY_NODE_ENV" BUILD_DIR="$BUILD_DIR" DEPLOY_LOCAL_PATH="$DEPLOY_LOCAL_PATH" "$deploy_script"
}

deploy_with_command() {
  run_shell_command "export NODE_ENV=$(printf '%q' "$DEPLOY_NODE_ENV") BUILD_DIR=$(printf '%q' "$BUILD_DIR") DEPLOY_LOCAL_PATH=$(printf '%q' "$DEPLOY_LOCAL_PATH"); ${DEPLOY_COMMAND:?}"
}

deploy_with_aws() {
  local aws_script="$ROOT_DIR/scripts/deploy-aws.sh"

  if [[ ! -x "$aws_script" ]]; then
    echo "$SCRIPT_NAME: AWS deployment helper is not executable: $aws_script" >&2
    exit 1
  fi

  run env NODE_ENV="$DEPLOY_NODE_ENV" BUILD_DIR="$BUILD_DIR" DEPLOY_LOCAL_PATH="$DEPLOY_LOCAL_PATH" "$aws_script"
}

deploy_with_rsync() {
  local deploy_user source_dir

  require_command rsync
  source_dir="${DEPLOY_LOCAL_PATH:-$BUILD_DIR}"
  deploy_user="${DEPLOY_USER:-$USER}"

  if [[ ! -d "$source_dir" ]]; then
    echo "$SCRIPT_NAME: rsync source directory not found: $source_dir" >&2
    exit 1
  fi

  run rsync -az --delete -e "ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new" "${source_dir}/" "${deploy_user}@${DEPLOY_HOST}:${DEPLOY_PATH}/"
}

deploy_to_production() {
  verify_deploy_source

  if [[ -n "${DEPLOY_SCRIPT:-}" ]]; then
    deploy_with_script
  elif [[ -n "${DEPLOY_COMMAND:-}" ]]; then
    deploy_with_command
  elif [[ "${DEPLOY_PROVIDER:-}" == "aws" ]] || [[ -n "${DEPLOY_S3_BUCKET:-}" ]] || [[ -n "${DEPLOY_ECS_CLUSTER:-}" ]] || [[ -n "${DEPLOY_LAMBDA_FUNCTION:-}" ]]; then
    deploy_with_aws
  elif [[ -n "${DEPLOY_HOST:-}" && -n "${DEPLOY_PATH:-}" ]]; then
    deploy_with_rsync
  else
    echo "$SCRIPT_NAME: set DEPLOY_SCRIPT, DEPLOY_COMMAND, DEPLOY_PROVIDER=aws, or DEPLOY_HOST and DEPLOY_PATH" >&2
    exit 1
  fi
}

run_pipeline_steps() {
  local test_pid=0
  local build_pid=0
  local test_status=0
  local build_status=0

  install_dependencies

  if [[ "$SKIP_TESTS" == "1" && "$SKIP_BUILD" == "1" ]]; then
    return 0
  fi

  if [[ "$RUN_IN_PARALLEL" == "1" && "$SKIP_TESTS" != "1" && "$SKIP_BUILD" != "1" ]]; then
    run_test_step &
    test_pid=$!
    run_build_step &
    build_pid=$!

    wait "$test_pid" || test_status=$?
    wait "$build_pid" || build_status=$?

    if [[ "$test_status" -ne 0 ]]; then
      exit "$test_status"
    fi
    if [[ "$build_status" -ne 0 ]]; then
      exit "$build_status"
    fi
    return 0
  fi

  run_test_step
  run_build_step
}

main() {
  detect_package_manager
  run_pipeline_steps
  deploy_to_production
}

main "$@"