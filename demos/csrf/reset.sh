#!/usr/bin/env bash
# Restore csrf/ to its as-committed state.
#
# Removes runtime artifacts produced by run-demo.sh:
#   - /tmp/csrf_server.log
#
# Does NOT touch:
#   - node_modules/      (kept; expensive to re-install)
#   - package-lock.json  (kept; npm regenerates it but it caches resolution)

set -e
cd "$(dirname "$0")"

removed=0
if [ -f /tmp/csrf_server.log ]; then
    rm -f /tmp/csrf_server.log
    echo "  removed /tmp/csrf_server.log"
    removed=$((removed + 1))
fi

if [ "$removed" -eq 0 ]; then
    echo "  already clean"
fi
