#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

if ! command -v node >/dev/null 2>&1; then
    echo "node not found. Install Node.js." >&2
    exit 1
fi

if [ ! -d node_modules ]; then
    echo "[harness] installing deps..."
    npm install --silent --no-audit --no-fund
fi

node server.js >/tmp/graphql-dos-server.log 2>&1 &
SERVER_PID=$!
trap 'kill $SERVER_PID 2>/dev/null || true' EXIT

# Wait for server (Apollo prints "Server ready at http://...")
for _ in $(seq 1 100); do
    if grep -q "Server ready" /tmp/graphql-dos-server.log 2>/dev/null; then break; fi
    sleep 0.1
done

node exploit.js
