#!/usr/bin/env bash
# Restore file-upload/ to its as-committed state.
#
# Removes runtime artifacts produced by run-demo.sh:
#   - uploads/                    (every uploaded file)
#   - __pycache__/                (Python bytecode cache)
#   - /tmp/file_upload_server.log

set -e
cd "$(dirname "$0")"

removed=0
if [ -d uploads ]; then
    rm -rf uploads
    echo "  removed uploads/"
    removed=$((removed + 1))
fi
if [ -d __pycache__ ]; then
    rm -rf __pycache__
    echo "  removed __pycache__/"
    removed=$((removed + 1))
fi
if [ -f /tmp/file_upload_server.log ]; then
    rm -f /tmp/file_upload_server.log
    echo "  removed /tmp/file_upload_server.log"
    removed=$((removed + 1))
fi

if [ "$removed" -eq 0 ]; then
    echo "  already clean"
fi
