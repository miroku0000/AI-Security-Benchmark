#!/usr/bin/env bash
# Restore idor/ to its as-committed state.
#
# Removes runtime artifacts produced by run-demo.sh:
#   - __pycache__/         (Python bytecode cache)
#   - /tmp/idor_server.log (server log)
#
# Does NOT touch any committed file. invoices/invoice_1.pdf and
# invoices/invoice_2.pdf are committed fixtures (the data the
# application serves); edits to them persist across runs. To restore
# the original fixture contents, use:
#   git checkout invoices/

set -e
cd "$(dirname "$0")"

removed=0
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
