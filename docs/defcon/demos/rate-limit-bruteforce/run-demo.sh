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
    echo "[harness] installing deps (mongodb-memory-server downloads ~100MB on first run)..."
    npm install --silent --no-audit --no-fund
fi

# Start server
node server.js >/tmp/rate-limit-server.log 2>&1 &
SERVER_PID=$!
trap 'kill $SERVER_PID 2>/dev/null || true' EXIT

# Wait for it to be ready
for _ in $(seq 1 100); do
    if curl -sf -o /dev/null -X POST -H 'Content-Type: application/json' \
            -d '{"username":"healthcheck","password":"x"}' \
            http://127.0.0.1:3098/api/login; then
        break
    fi
    if curl -s -o /dev/null -w '%{http_code}' -X POST -H 'Content-Type: application/json' \
            -d '{"username":"healthcheck","password":"x"}' \
            http://127.0.0.1:3098/api/login | grep -q '^4'; then
        break
    fi
    sleep 0.1
done

python3 exploit.py
