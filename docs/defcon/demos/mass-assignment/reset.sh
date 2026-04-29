#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
rm -rf __pycache__ /tmp/mass-assignment-server.log
echo "reset complete"
