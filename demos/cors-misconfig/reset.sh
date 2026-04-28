#!/usr/bin/env bash
# Restore cors-misconfig/ to its as-committed state.
#
# Removes runtime artifacts produced by run-demo.sh:
#   - __pycache__/                       (Python bytecode cache)
#   - /tmp/cors_misconfig_server.log

set -e
cd "$(dirname "$0")"

removed=0
if [ -d __pycache__ ]; then
    rm -rf __pycache__
    echo "  removed __pycache__/"
    removed=$((removed + 1))
fi
if [ -f /tmp/cors_misconfig_server.log ]; then
    rm -f /tmp/cors_misconfig_server.log
    echo "  removed /tmp/cors_misconfig_server.log"
    removed=$((removed + 1))
fi

if [ "$removed" -eq 0 ]; then
    echo "  already clean"
fi
