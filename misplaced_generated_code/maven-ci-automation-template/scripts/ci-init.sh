#!/usr/bin/env bash
set -euo pipefail
mkdir -p "${CI_BUILD_TARGET_DIR}/ci-init"
echo "initialized at $(date -u +%Y-%m-%dT%H:%M:%SZ) version=${CI_PROJECT_VERSION}" > "${CI_BUILD_TARGET_DIR}/ci-init/init.txt"
