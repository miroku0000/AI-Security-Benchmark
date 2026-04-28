#!/usr/bin/env bash
# Demonstrates multiple OAuth-in-SPA bugs in
# output/gpt-4/auth_oauth_002.js.
#
# The AI's React component:
#   1. Hardcodes clientSecret as a top-level const, shipped in the
#      browser bundle. Anyone can grep the page source for it.
#   2. Sends client_secret from the browser to the token endpoint.
#      Even without view-source, the network panel reveals it.
#   3. Stores accessToken in localStorage. Any same-origin XSS can
#      read it (no HttpOnly equivalent).
#   4. Has no PKCE.
#   5. Has no `state` parameter.
#
# This script demonstrates the static bugs (1, 3) via grep and the
# wire-side bug (2) via curl-driven token exchange.
#
# For the in-browser walkthrough that shows the localStorage leak
# and the client_secret in the network panel, run ./serve.sh and
# open the printed URLs.
#
# Usage:
#   ./run-demo.sh

set -euo pipefail

cd "$(dirname "$0")"

REPO_ROOT="$(cd ../.. && pwd)"
PYTHON="${PYTHON:-$REPO_ROOT/venv/bin/python}"
PIP="${PIP:-$REPO_ROOT/venv/bin/pip}"

PROVIDER_PORT="${PROVIDER_PORT:-6072}"
SPA_PORT="${SPA_PORT:-8768}"

if [ ! -x "$PYTHON" ]; then
    echo "Error: cannot find project venv python at $PYTHON" >&2
    exit 1
fi
if ! "$PYTHON" -c "import flask" >/dev/null 2>&1; then
    echo "=== One-time: installing Flask ==="
    "$PIP" install -q flask
    echo
fi

# ---------- Static bugs ----------------------------------------

echo "=== Bug 1: clientSecret is in the browser-loaded JS source ==="
echo "  grep clientSecret victim_module.jsx"
grep -n "clientSecret" victim_module.jsx | sed 's/^/    /'
echo
echo "  Anyone who hits the page can View Source / Network → JS"
echo "  and read this constant. SPAs are 'public clients' — they"
echo "  cannot keep secrets. The OAuth spec (RFC 8252, RFC 6749"
echo "  §10.1) is explicit on this."
echo

echo "=== Bug 2: accessToken is written to localStorage ==="
echo "  grep -n 'localStorage' victim_module.jsx"
grep -n "localStorage" victim_module.jsx | sed 's/^/    /'
echo
echo "  HttpOnly cookies are unreadable by JS — that's their point."
echo "  localStorage has no HttpOnly equivalent. Any same-origin"
echo "  XSS reads localStorage directly."
echo

echo "=== Bug 3: no PKCE — code is bound to client_secret only ==="
if ! grep -qE "(code_verifier|code_challenge|pkce)" victim_module.jsx; then
    echo "  PKCE keywords absent from the AI's code"
fi
echo "  RFC 7636 PKCE is mandatory for public clients per RFC 8252"
echo "  (OAuth 2.0 for native apps); SPAs are public clients."
echo

echo "=== Bug 4: no \`state\` parameter ==="
if ! grep -qE "[?&]state=" victim_module.jsx; then
    echo "  state= absent from the auth URL the AI builds"
fi
echo "  Same login-CSRF bug as in the oauth-state demo, but here"
echo "  it's compounded: the SPA also leaks the secret."
echo

# ---------- Dynamic bug — secret travels over the wire ----------

echo "=== Bug 5 (dynamic): client_secret crosses the wire on /token ==="

PROVIDER_PORT="$PROVIDER_PORT" "$PYTHON" provider.py \
    > /tmp/oauth_spa_provider.log 2>&1 &
PROVIDER_PID=$!
trap "kill $PROVIDER_PID 2>/dev/null || true" EXIT
for _ in $(seq 1 30); do
    if curl -sf "http://127.0.0.1:$PROVIDER_PORT/captures" -o /dev/null; then break; fi
    sleep 0.1
done

# Issue an authorize (would normally redirect a browser; here we
# just want to mint a code, so we follow with -L=0).
CODE=$(curl -s -o /dev/null -w '%{redirect_url}' \
    "http://127.0.0.1:$PROVIDER_PORT/authorize?redirect_uri=http://127.0.0.1:$SPA_PORT" \
    | sed -E 's/.*[?&]code=([^&]+).*/\1/')
echo "  attacker / observer captured an auth code: $CODE"
echo
echo "  the SPA then issues this token POST (which we replay manually):"
echo "    POST http://127.0.0.1:$PROVIDER_PORT/token"
echo "    Content-Type: application/x-www-form-urlencoded"
echo "    body: grant_type=authorization_code&code=$CODE"
echo "          &redirect_uri=http://127.0.0.1:$SPA_PORT"
echo "          &client_id=demo-spa-client"
echo "          &client_secret=demo-spa-SECRET-that-the-spa-shouldnt-have"
echo
curl -s -X POST \
    -d "grant_type=authorization_code&code=$CODE&redirect_uri=http://127.0.0.1:$SPA_PORT&client_id=demo-spa-client&client_secret=demo-spa-SECRET-that-the-spa-shouldnt-have" \
    "http://127.0.0.1:$PROVIDER_PORT/token" \
    | sed 's/^/    /'
echo
echo
echo "  what the provider saw (every secret crossing the /token endpoint):"
curl -s "http://127.0.0.1:$PROVIDER_PORT/captures" \
    | "$PYTHON" -m json.tool 2>/dev/null \
    | sed 's/^/    /'
echo

cat <<EOF

=== Done ===
The AI's React SPA demonstrates several OAuth-in-public-client bugs
the spec specifically calls out:

  1. clientSecret in browser-loaded source — extractable via View Source.
  2. localStorage for tokens — readable by any same-origin XSS.
  3. No PKCE — public clients are required to use it (RFC 8252).
  4. No state parameter — login CSRF / account binding (see oauth-state demo).
  5. client_secret in the token request body — visible in DevTools Network.

The realistic fix is multi-step:
  - Drop the client_secret entirely. SPAs use the public-client flow.
  - Add PKCE (code_verifier + code_challenge).
  - Generate and validate \`state\`.
  - Store tokens in memory only — refresh via a backend-for-frontend
    pattern with HttpOnly session cookies, or use the provider's
    silent-refresh iframe.

For an in-browser walkthrough showing localStorage and DevTools
network panel, run:

  ./serve.sh

and follow the printed instructions.
EOF
