#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

if ! command -v node >/dev/null 2>&1; then
    echo "node not found. Install Node.js (https://nodejs.org or 'brew install node')." >&2
    exit 1
fi
if ! command -v npm >/dev/null 2>&1; then
    echo "npm not found." >&2
    exit 1
fi

if [ ! -d node_modules ]; then
    echo "[harness] installing deps (hardhat-toolbox is large; first run only)..."
    npm install --silent --no-audit --no-fund
fi

# Hardhat compiles on first run; suppress its progress chatter unless DEMO_VERBOSE set.
if [ "${DEMO_VERBOSE:-0}" = "1" ]; then
    npx hardhat run exploit.js
else
    # Hardhat's own banner goes to stderr; tests' console.log to stdout
    npx hardhat run exploit.js 2>/dev/null
fi
