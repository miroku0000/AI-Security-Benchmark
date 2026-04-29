#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

if ! command -v node >/dev/null 2>&1; then
    echo "node not found. Install Node.js." >&2
    exit 1
fi
if ! command -v python3 >/dev/null 2>&1; then
    echo "python3 not found." >&2
    exit 1
fi

echo "=== Step 1: AI's hashPassword() runs at registration time ==="
node seed.js sunshine
echo

echo "=== Step 2: attacker steals leaked-hash.txt and runs offline crack ==="
python3 crack.py
