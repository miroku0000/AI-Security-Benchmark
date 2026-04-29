#!/usr/bin/env bash
# Restore open-redirect/ to its as-committed state.
#
# Removes runtime artifacts produced by run-demo.sh:
#   - /tmp/open_redirect_server.log  (server log)
#
# Does NOT touch:
#   - node_modules/      (kept; expensive to re-install Express each run)
#   - package-lock.json  (kept; npm regenerates it but it caches resolution)
# Use `rm -rf node_modules package-lock.json` manually if you want to
# stage a fresh `npm install` for the demo.

set -e
cd "$(dirname "$0")"

removed=0
if [ -f /tmp/open_redirect_server.log ]; then
    rm -f /tmp/open_redirect_server.log
    echo "  removed /tmp/open_redirect_server.log"
    removed=$((removed + 1))
fi

if [ "$removed" -eq 0 ]; then
    echo "  already clean"
fi
