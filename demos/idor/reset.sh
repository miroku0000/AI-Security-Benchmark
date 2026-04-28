#!/usr/bin/env bash
# Restore idor/ to its as-committed state.
#
# Removes runtime artifacts produced by run-demo.sh:
#   - invoices/        (seed PDF directory)
#   - __pycache__/     (Python bytecode cache)
#
# Does NOT touch any committed file.

set -e
cd "$(dirname "$0")"

removed=0
if [ -d invoices ]; then
    rm -rf invoices
    echo "  removed invoices/"
    removed=$((removed + 1))
fi
if [ -d __pycache__ ]; then
    rm -rf __pycache__
    echo "  removed __pycache__/"
    removed=$((removed + 1))
fi
if [ -f /tmp/idor_server.log ]; then
    rm -f /tmp/idor_server.log
    echo "  removed /tmp/idor_server.log"
    removed=$((removed + 1))
fi

if [ "$removed" -eq 0 ]; then
    echo "  already clean"
fi
