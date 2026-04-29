#!/usr/bin/env bash
# Restore sql-injection/ to its as-committed state.
#
# Removes runtime artifacts produced by run-demo.sh:
#   - demo.sqlite     (re-seeded on each run anyway)
#   - __pycache__/    (Python bytecode cache)
#
# Does NOT touch any committed file.

set -e
cd "$(dirname "$0")"

removed=0
if [ -f demo.sqlite ]; then
    rm -f demo.sqlite
    echo "  removed demo.sqlite"
    removed=$((removed + 1))
fi
if [ -d __pycache__ ]; then
    rm -rf __pycache__
    echo "  removed __pycache__/"
    removed=$((removed + 1))
fi

if [ "$removed" -eq 0 ]; then
    echo "  already clean"
fi
