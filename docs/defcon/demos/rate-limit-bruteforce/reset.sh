#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
rm -rf __pycache__ /tmp/rate-limit-server.log
# leave node_modules in place to avoid re-downloading mongodb-memory-server
echo "reset complete (node_modules retained)"
