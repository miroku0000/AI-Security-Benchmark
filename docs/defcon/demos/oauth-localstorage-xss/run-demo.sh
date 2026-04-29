#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

if ! command -v node >/dev/null 2>&1; then
    echo "node not found." >&2
    exit 1
fi

if [ ! -d node_modules ]; then
    echo "[harness] installing deps (jsdom)..."
    npm install --silent --no-audit --no-fund
fi

node exploit.js
