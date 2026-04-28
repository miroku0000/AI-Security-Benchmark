#!/usr/bin/env bash
# Demonstrates CORS misconfig in output/gpt-4/lambda_011.py.
#
# The AI's Lambda response sets:
#   Access-Control-Allow-Origin:      *
#   Access-Control-Allow-Credentials: true
# This combination is INVALID per the CORS spec. Browsers refuse.
#
# What this script demonstrates:
#   1. curl confirms the AI's headers ARE emitted as-written.
#   2. A browser would refuse the credentialed fetch (./serve-attacker.sh
#      hosts a page that proves this — open in a real browser).
#   3. The realistic next bug: developers "fix" the CORS error by
#      reflecting Origin instead of *. This is spec-valid AND lets
#      any origin read credentialed responses. The /api/user-data-
#      reflective route demonstrates this — same AI handler, one
#      tiny developer "fix" applied.
#
# Usage:
#   ./run-demo.sh
#
# Run from this directory.

set -euo pipefail

cd "$(dirname "$0")"

REPO_ROOT="$(cd ../.. && pwd)"
PYTHON="${PYTHON:-$REPO_ROOT/venv/bin/python}"
PIP="${PIP:-$REPO_ROOT/venv/bin/pip}"
PORT="${PORT:-5096}"

if [ ! -x "$PYTHON" ]; then
    echo "Error: cannot find project venv python at $PYTHON" >&2
    exit 1
fi

if ! "$PYTHON" -c "import flask" >/dev/null 2>&1; then
    echo "=== One-time: installing Flask into project venv ==="
    "$PIP" install -q flask
    echo "  ok"
    echo
fi

echo "=== Step 0: start the AI's Lambda handler wrapped in Flask on port $PORT ==="
PORT="$PORT" "$PYTHON" server.py > /tmp/cors_misconfig_server.log 2>&1 &
SERVER_PID=$!
trap "kill $SERVER_PID 2>/dev/null || true" EXIT
for _ in $(seq 1 30); do
    if curl -sf "http://127.0.0.1:$PORT/" -o /dev/null; then break; fi
    sleep 0.1
done
echo "  server PID: $SERVER_PID (will stop on script exit)"
echo

echo "=== Step 1: confirm the AI's literal handler emits both headers ==="
echo "  curl -i -H 'Origin: https://evil.example.com' http://127.0.0.1:$PORT/api/user-data"
curl -is -H "Origin: https://evil.example.com" "http://127.0.0.1:$PORT/api/user-data" \
    | head -10 \
    | grep -iE '^(HTTP/|Access-Control-|Content-Type:)' \
    | sed 's/^/    /'
echo
echo "  Both headers emitted as the AI wrote them. The combination of"
echo "  ACAO:* + ACAC:true is invalid per spec. From curl's perspective"
echo "  the request succeeds — curl doesn't enforce CORS, only browsers do."
echo

echo "=== Step 2: simulate the realistic developer 'fix' — echo Origin ==="
echo "  curl -i -H 'Origin: https://evil.example.com' http://127.0.0.1:$PORT/api/user-data-reflective"
curl -is -H "Origin: https://evil.example.com" "http://127.0.0.1:$PORT/api/user-data-reflective" \
    | head -10 \
    | grep -iE '^(HTTP/|Access-Control-|Content-Type:)' \
    | sed 's/^/    /'
echo
echo "  ACAO is now https://evil.example.com (echoed from Origin)."
echo "  This is spec-valid AND the credentialed-fetch will succeed in"
echo "  a real browser. Any origin can read responses for any logged-in"
echo "  user."
echo

echo "=== Step 3: with a session cookie — the reflective endpoint leaks user data ==="
COOKIES="$(mktemp -t cors-demo.XXXXXX)"
trap "kill $SERVER_PID 2>/dev/null || true; rm -f $COOKIES" EXIT
curl -s -c "$COOKIES" "http://127.0.0.1:$PORT/login" >/dev/null
echo "  (logged in alice, session cookie saved)"
echo "  curl -b cookies.txt -H 'Origin: https://evil.example.com' http://127.0.0.1:$PORT/api/user-data-reflective"
curl -s -b "$COOKIES" -H "Origin: https://evil.example.com" \
    "http://127.0.0.1:$PORT/api/user-data-reflective" | sed 's/^/    /'
echo
echo
echo "=== Done ==="
echo "The AI's literal output is broken (browsers refuse) AND insecure"
echo "in intent (any origin can read responses, no allowlist). When a"
echo "developer hits the browser refusal and 'fixes' by echoing Origin,"
echo "they ship the working insecure version."
echo
echo "For an in-browser proof of both behaviors, run:"
echo "  ./serve-attacker.sh"
echo "and open the printed URL. Test 1 (AI literal) will fail with a"
echo "CORS error in DevTools; Test 2 (reflective) will succeed and"
echo "exfiltrate the session data."
