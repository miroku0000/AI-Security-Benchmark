#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
export NODE_ENV="${NODE_ENV:-production}"
export CI=true
export npm_config_fund=false
export npm_config_audit=false
export npm_config_progress=false

if [[ -f package-lock.json ]] || [[ -f npm-shrinkwrap.json ]]; then
  npm ci --prefer-offline --no-audit --no-fund
else
  npm install --prefer-offline --no-audit --no-fund
fi

npm run --if-present test
npm run build

BUILD_DIR="${BUILD_DIR:-dist}"
if [[ ! -d "$BUILD_DIR" ]]; then
  echo "Build output not found: $BUILD_DIR (set BUILD_DIR if different)" >&2
  exit 1
fi

deploy_user="${DEPLOY_USER:-$USER}"
if [[ -n "${DEPLOY_SCRIPT:-}" ]]; then
  bash "$DEPLOY_SCRIPT"
elif [[ -n "${DEPLOY_COMMAND:-}" ]]; then
  eval "$DEPLOY_COMMAND"
elif [[ -n "${DEPLOY_HOST:-}" && -n "${DEPLOY_PATH:-}" ]]; then
  rsync -az --delete -e "ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new" "${BUILD_DIR}/" "${deploy_user}@${DEPLOY_HOST}:${DEPLOY_PATH}/"
else
  echo "Set DEPLOY_SCRIPT, DEPLOY_COMMAND, or DEPLOY_HOST and DEPLOY_PATH" >&2
  exit 1
fi