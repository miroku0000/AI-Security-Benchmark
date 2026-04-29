#!/usr/bin/env bash
# Restore nosql-injection/ to its as-committed state.
#
# Removes runtime artifacts produced by run-demo.sh:
#   - /tmp/nosql_server.log
#
# Does NOT touch:
#   - node_modules/      (kept; mongodb-memory-server is ~100MB, slow to re-fetch)
#   - package-lock.json  (kept; npm regenerates it but it caches resolution)

set -e
cd "$(dirname "$0")"

removed=0
if [ -f /tmp/nosql_server.log ]; then
    rm -f /tmp/nosql_server.log
    echo "  removed /tmp/nosql_server.log"
    removed=$((removed + 1))
fi

if [ "$removed" -eq 0 ]; then
    echo "  already clean"
fi
