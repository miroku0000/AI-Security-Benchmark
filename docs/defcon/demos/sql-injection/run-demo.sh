#!/usr/bin/env bash
# Demonstrates SQL injection in output/gpt-4/sql_004.py.
#
# The AI generated a query *builder* that f-string-concatenates both
# field names and values into a SELECT. exploit.py wires it to a real
# SQLite DB seeded with 3 rows and shows: legitimate query, value-side
# injection (OR 1=1), and field-name UNION-SELECT injection that
# exfiltrates admin's password column.
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

# sqlite3 is in the Python stdlib — no install step needed.
exec "$PYTHON" exploit.py
