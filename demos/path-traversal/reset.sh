#!/usr/bin/env bash
# Restore path-traversal/ to its as-committed state.
#
# This demo has no harness-generated artifacts to clean up — the
# legitimate-request fixture lives at logs/app.log and is committed,
# so reset is a no-op by design.
#
# Does NOT touch:
#   - logs/              (committed fixture; edits persist)
#   - node_modules/      (kept; expensive to re-install Express each run)
#   - package-lock.json  (kept; npm regenerates it but it caches resolution)
# Use `rm -rf node_modules package-lock.json` manually if you want to
# stage a fresh `npm install` for the demo.
#
# To restore the original logs/app.log content:
#   git checkout logs/

set -e
cd "$(dirname "$0")"

# Clean up the legacy /tmp location from previous demo versions.
removed=0
if [ -d /tmp/path-traversal-demo-logs ]; then
    rm -rf /tmp/path-traversal-demo-logs
    echo "  removed legacy /tmp/path-traversal-demo-logs/"
    removed=$((removed + 1))
fi

if [ "$removed" -eq 0 ]; then
    echo "  already clean"
fi
