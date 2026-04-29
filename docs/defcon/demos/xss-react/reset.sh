#!/usr/bin/env bash
# Restore xss-react/ to its as-committed state.
#
# Removes runtime artifacts produced by run-demo.sh:
#   - out/   (rendered HTML files: legitimate, alert, defacement, cookie-display)
#
# Does NOT touch:
#   - node_modules/      (kept; expensive to reinstall)
#   - package-lock.json  (kept)
# Use `rm -rf node_modules package-lock.json` manually if you want to
# stage a fresh `npm install` for the demo.
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
