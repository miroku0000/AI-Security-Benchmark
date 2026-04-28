#!/usr/bin/env bash
# Restore ssrf/ to its as-committed state.
#
# Removes runtime artifacts produced by run-demo.sh:
#   - __pycache__/   (Python bytecode cache)
#
# The fake IMDS server runs in-process and binds 127.0.0.1:8169 only
# while run-demo.sh is alive (run-demo.sh kills it on exit). No
# persistent server state to clean up.
#
# Does NOT touch any committed file.

set -e
cd "$(dirname "$0")"

if [ -d __pycache__ ]; then
    rm -rf __pycache__
    echo "  removed __pycache__/"
else
    echo "  already clean"
fi
