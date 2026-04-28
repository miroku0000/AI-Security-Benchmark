#!/usr/bin/env bash
# Reset all demos to their as-committed state.
#
# Calls each demo's reset.sh in turn. Each reset.sh removes only the
# runtime artifacts that demo's run-demo.sh produces — node_modules/
# and other expensive-to-regenerate scaffolding are kept. See the
# individual reset.sh scripts for details.
#
# Usage:
#   ./reset-all.sh

set -e
cd "$(dirname "$0")"

for demo in jwt-weak-secret pickle-rce command-injection ssrf path-traversal idor xss-react xxe-java xss-wordpress; do
    if [ -x "$demo/reset.sh" ]; then
        echo "=== $demo ==="
        "$demo/reset.sh"
        echo
    else
        echo "=== $demo (no reset.sh; skipping) ==="
        echo
    fi
done
