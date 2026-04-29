#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

if ! command -v node >/dev/null 2>&1; then
    echo "node not found. Install Node.js (e.g. https://nodejs.org or 'brew install node')." >&2
    exit 1
fi
if ! command -v npm >/dev/null 2>&1; then
    echo "npm not found." >&2
    exit 1
fi

if [ ! -d node_modules ]; then
    echo "[harness] installing deps..."
    npm install --silent --no-audit --no-fund
fi

# Start server
node server.js >/tmp/node-deserialize-server.log 2>&1 &
SERVER_PID=$!
trap 'kill $SERVER_PID 2>/dev/null || true' EXIT

# Wait for it
for _ in $(seq 1 50); do
    if curl -sf -o /dev/null http://127.0.0.1:3099/ ; then break; fi
    if curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:3099/ | grep -qE '^[0-9]'; then break; fi
    sleep 0.1
done

node exploit.js
