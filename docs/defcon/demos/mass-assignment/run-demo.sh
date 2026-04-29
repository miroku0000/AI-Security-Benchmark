#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

VENV="../../.venv-demos"
if [ ! -d "$VENV" ]; then
    python3 -m venv "$VENV"
fi
# shellcheck disable=SC1091
source "$VENV/bin/activate"

python -c 'import flask, flask_login' 2>/dev/null || pip install -q flask flask-login >/dev/null

# Start the AI's Flask app (with harness wrapper)
python server.py 3010 >/tmp/mass-assignment-server.log 2>&1 &
SERVER_PID=$!
trap 'kill $SERVER_PID 2>/dev/null || true' EXIT

# Wait for the server
for _ in $(seq 1 50); do
    if curl -sf http://127.0.0.1:3010/profile >/dev/null 2>&1; then
        break
    fi
    sleep 0.1
done

python exploit.py
