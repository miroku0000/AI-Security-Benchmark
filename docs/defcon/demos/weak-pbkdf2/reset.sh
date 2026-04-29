#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
rm -f leaked-hash.txt
rm -rf __pycache__
echo "reset complete"
