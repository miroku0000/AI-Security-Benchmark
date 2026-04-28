#!/usr/bin/env bash
# Restore ldap-injection/ to its as-committed state.
#
# Removes runtime artifacts produced by run-demo.sh:
#   - __pycache__/    (Python bytecode cache)
#
# slapd's config + DB live in /tmp under a per-run tempdir that is
# torn down on script exit, so there's nothing persistent to clean.

set -e
cd "$(dirname "$0")"

removed=0
if [ -d __pycache__ ]; then
    rm -rf __pycache__
    echo "  removed __pycache__/"
    removed=$((removed + 1))
fi

if [ "$removed" -eq 0 ]; then
    echo "  already clean"
fi
