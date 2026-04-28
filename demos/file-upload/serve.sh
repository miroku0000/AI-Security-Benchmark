#!/usr/bin/env bash
# Keep the AI's app running so you can browse uploaded files.
# (run-demo.sh kills the server on exit; this leaves it running.)
#
# Usage:
#   ./serve.sh             # uses port 5095
#   PORT=8080 ./serve.sh   # custom port

set -e
cd "$(dirname "$0")"

REPO_ROOT="$(cd ../.. && pwd)"
PYTHON="${PYTHON:-$REPO_ROOT/venv/bin/python}"
PORT="${PORT:-5095}"

if ! "$PYTHON" -c "import flask" >/dev/null 2>&1; then
    "$REPO_ROOT/venv/bin/pip" install -q flask
fi

echo "Starting AI upload app on http://127.0.0.1:$PORT"
echo "  - Index:           http://127.0.0.1:$PORT/"
echo "  - Upload via curl: curl -F file=@your-file.html http://127.0.0.1:$PORT/upload"
echo "  - Uploaded files:  http://127.0.0.1:$PORT/uploads/<name>"
echo
exec env PORT="$PORT" "$PYTHON" server.py
