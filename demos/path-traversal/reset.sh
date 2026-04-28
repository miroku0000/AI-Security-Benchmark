#!/usr/bin/env bash
# Restore path-traversal/ to its as-committed state.
#
# Removes runtime artifacts produced by run-demo.sh:
#   - /tmp/path-traversal-demo-logs/   (log directory the demo seeds for
#                                       the legitimate-request step)
#
# Does NOT touch:
#   - node_modules/      (kept; expensive to re-install Express each run)
#   - package-lock.json  (kept; npm regenerates it but it caches resolution)
# Use `rm -rf node_modules package-lock.json` manually if you want to
# stage a fresh `npm install` for the demo.
#
# Does NOT touch any committed file.

set -e
cd "$(dirname "$0")"

removed=0
if [ -d /tmp/path-traversal-demo-logs ]; then
    rm -rf /tmp/path-traversal-demo-logs
    echo "  removed /tmp/path-traversal-demo-logs/"
    removed=$((removed + 1))
fi

if [ "$removed" -eq 0 ]; then
    echo "  already clean"
fi
