#!/usr/bin/env bash
# Demonstrates Cross-Site Scripting (XSS) in output/gpt-4/xss_003.js.
# The AI's UserBio React component uses dangerouslySetInnerHTML on a
# user-controlled prop. Whatever HTML lives in `bio` gets injected.
#
# We render the component server-side via react-dom/server, then write
# each render as a standalone .html file in out/. You can:
#   - read the rendered HTML in stdout to inspect the injected tags
#   - open out/*.html in a browser via file://
#   - run ./serve.sh and load http://localhost:8765/ for a fully
#     realistic browser-execution demo
#
# Usage:
#   ./run-demo.sh
#
# Run from this directory.

set -e

cd "$(dirname "$0")"

if [ ! -d node_modules ]; then
    echo "=== One-time: installing React + Babel (~10 seconds) ==="
    npm install --silent
    echo
fi

node exploit.js

echo
echo "=== Done ==="
echo "Open one of the generated files in a browser to see each payload"
echo "execute. The alert.html and defacement.html pages are the most"
echo "visible on stage — alert popping a dialog, defacement replacing"
echo "the page body with a red 'Hijacked by attacker' banner."
echo
echo "For an http:// demo (recommended, behaves identically to a real"
echo "victim hitting the live site), run: ./serve.sh"
