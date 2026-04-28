#!/usr/bin/env bash
# Restore xss-react/ to its as-committed state.
#
# This demo produces no runtime artifacts in its own directory beyond
# node_modules/ (which we deliberately keep — Babel + React install is
# the slow step). The exploit prints to stdout only.
#
# Does NOT touch:
#   - node_modules/      (kept)
#   - package-lock.json  (kept)
# Use `rm -rf node_modules package-lock.json` manually if you want to
# stage a fresh `npm install` for the demo.
#
# Does NOT touch any committed file.

set -e
cd "$(dirname "$0")"

echo "  already clean (this demo writes nothing to its own directory)"
