#!/usr/bin/env bash
# Restore xss-wordpress/ to its as-committed state.
#
# Removes runtime artifacts produced by run-demo.sh:
#   - out/   (rendered HTML files: legitimate, alert, defacement, cookie-display)
#
# Does NOT touch any committed file.

set -e
cd "$(dirname "$0")"

if [ -d out ]; then
    rm -rf out
    echo "  removed out/"
else
    echo "  already clean"
fi
