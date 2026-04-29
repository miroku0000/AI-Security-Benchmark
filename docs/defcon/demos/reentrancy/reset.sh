#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
rm -rf cache artifacts
echo "reset complete (node_modules retained)"
