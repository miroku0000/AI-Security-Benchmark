#!/usr/bin/env bash
# Restore pickle-rce/ to its as-committed state.
#
# Removes runtime artifacts produced by run-demo.sh:
#   - PWNED.txt        (marker file written by the RCE payload)
#   - preferences.pkl  (malicious pickle dropped by attacker.py)
#   - __pycache__/     (Python bytecode cache)
#
# Does NOT touch any committed file.

set -e
cd "$(dirname "$0")"

removed=0
for f in PWNED.txt preferences.pkl; do
    if [ -e "$f" ]; then
        rm -f "$f"
        echo "  removed $f"
        removed=$((removed + 1))
    fi
done
if [ -d __pycache__ ]; then
    rm -rf __pycache__
    echo "  removed __pycache__/"
    removed=$((removed + 1))
fi

if [ "$removed" -eq 0 ]; then
    echo "  already clean"
fi
