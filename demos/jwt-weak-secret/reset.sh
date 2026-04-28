#!/usr/bin/env bash
# Restore jwt-weak-secret/ to its as-committed state.
#
# Removes runtime artifacts produced by crack-and-forge.sh and the
# server scripts:
#   - /tmp/jwt_001_users.db    (SQLite DB the Flask server creates)
#   - /tmp/jwt_002_*.json      (any forged-token files crack-and-forge.sh
#                               or operators may have written)
#   - jwt_001/__pycache__/     (Python bytecode cache)
#
# Does NOT touch:
#   - jwt_002/node_modules/      (kept; expensive to re-install)
#   - jwt_002/package-lock.json  (kept)
# Use `rm -rf jwt_002/node_modules jwt_002/package-lock.json` manually
# if you want to stage a fresh `npm install` for the demo.
#
# Does NOT touch any committed file.

set -e
cd "$(dirname "$0")"

removed=0

# Flask demo SQLite DB (path the Flask app uses)
for f in /tmp/jwt_001_users.db /tmp/test.db; do
    if [ -f "$f" ]; then
        rm -f "$f"
        echo "  removed $f"
        removed=$((removed + 1))
    fi
done

# Any /tmp forged-token sidecars
for f in /tmp/jwt_001_forged.txt /tmp/jwt_002_forged.txt; do
    if [ -f "$f" ]; then
        rm -f "$f"
        echo "  removed $f"
        removed=$((removed + 1))
    fi
done

# Python bytecode cache
if [ -d jwt_001/__pycache__ ]; then
    rm -rf jwt_001/__pycache__
    echo "  removed jwt_001/__pycache__/"
    removed=$((removed + 1))
fi

if [ "$removed" -eq 0 ]; then
    echo "  already clean"
fi
