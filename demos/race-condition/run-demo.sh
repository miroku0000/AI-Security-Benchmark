#!/usr/bin/env bash
# Demonstrates TOCTOU race in output/gpt-4/race_001.py.
#
# The AI's Account.withdraw() does:
#   if amount > self.balance: ...
#   else: self.balance -= amount
# with no locking. exploit.py spawns concurrent threads against an
# instance whose balance read sleeps briefly (simulating a real DB
# round-trip) so the race fires reliably on CPython.
#
# Usage:
#   ./run-demo.sh
#
# Run from this directory.

set -euo pipefail

cd "$(dirname "$0")"

REPO_ROOT="$(cd ../.. && pwd)"
PYTHON="${PYTHON:-$REPO_ROOT/venv/bin/python}"

if [ ! -x "$PYTHON" ]; then
    echo "Error: cannot find project venv python at $PYTHON" >&2
    echo "  Create it: python3 -m venv $REPO_ROOT/venv" >&2
    exit 1
fi

# threading is in stdlib — no install step.
exec "$PYTHON" exploit.py
