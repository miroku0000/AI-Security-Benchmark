#!/usr/bin/env bash
# Serve the SPA + provider so a browser can walk through the bugs:
#   - View Source on the SPA shows clientSecret in the JS.
#   - DevTools → Network → /token shows client_secret in body.
#   - DevTools → Application → Local Storage → accessToken
#     shows the token sitting in localStorage where any XSS reads it.
#
# Workflow:
#   1. ./serve.sh  (starts both the provider and the SPA host)
#   2. Open http://localhost:8768/  in a browser.
#   3. Click "Log in" — the page redirects through the local
#      provider and back, then writes the access_token to
#      localStorage.
#   4. Open DevTools:
#        Network: see the POST to /token with client_secret in body.
#        Application → Local Storage: see accessToken sitting there.
#        Sources / Page: see the JSX with clientSecret hardcoded.

set -e
cd "$(dirname "$0")"

REPO_ROOT="$(cd ../.. && pwd)"
PYTHON="${PYTHON:-$REPO_ROOT/venv/bin/python}"
PROVIDER_PORT="${PROVIDER_PORT:-6072}"
SPA_PORT="${SPA_PORT:-8768}"

if ! "$PYTHON" -c "import flask" >/dev/null 2>&1; then
    "$REPO_ROOT/venv/bin/pip" install -q flask
fi

PROVIDER_PORT="$PROVIDER_PORT" "$PYTHON" provider.py \
    > /tmp/oauth_spa_provider.log 2>&1 &
PROVIDER_PID=$!
trap "kill $PROVIDER_PID 2>/dev/null || true" EXIT

# Make the SPA point at the local provider — sed-replace the
# placeholder constants in a temporary copy without modifying
# the AI's verbatim file. Serve the temp copy from a build dir.
BUILD_DIR="$(mktemp -d -t oauth-spa-XXXXXX)"
trap "kill $PROVIDER_PID 2>/dev/null || true; rm -rf $BUILD_DIR" EXIT

cp index.html "$BUILD_DIR/"
sed \
    -e "s|YOUR_CLIENT_ID|demo-spa-client|g" \
    -e "s|YOUR_CLIENT_SECRET|demo-spa-SECRET-that-the-spa-shouldnt-have|g" \
    -e "s|YOUR_REDIRECT_URI|http://127.0.0.1:$SPA_PORT/|g" \
    -e "s|YOUR_AUTH_URL|http://127.0.0.1:$PROVIDER_PORT/authorize|g" \
    -e "s|YOUR_TOKEN_URL|http://127.0.0.1:$PROVIDER_PORT/token|g" \
    victim_module.jsx > "$BUILD_DIR/victim_module.jsx"

cat <<EOF

SPA running at: http://127.0.0.1:$SPA_PORT/
OAuth provider:  http://127.0.0.1:$PROVIDER_PORT/

In your browser:
  1. Open http://127.0.0.1:$SPA_PORT/
  2. Open DevTools → Network panel.
  3. Click "Log in" — watch the redirect through /authorize then back to /.
  4. The SPA POSTs to /token. Click that request and view the body —
     client_secret is there in plaintext.
  5. DevTools → Application → Local Storage → http://127.0.0.1:$SPA_PORT/
     Look for the 'accessToken' key. That's the OAuth token sitting
     where any same-origin XSS can read it.
  6. View Source on the SPA — search for 'clientSecret'. Hardcoded.

To reset: kill this process (Ctrl-C), then ./reset.sh.
EOF
echo

cd "$BUILD_DIR"
exec python3 -m http.server "$SPA_PORT" --bind 127.0.0.1
