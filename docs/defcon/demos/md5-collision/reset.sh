#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
rm -f release-1.0.0-benign.bin release-1.0.0-backdoored.bin
rm -rf __pycache__
echo "reset complete"
