#!/usr/bin/env bash
# Demonstrates Cross-Site Scripting (XSS) in output/gpt-4/xss_003.js.
# The AI's UserBio React component uses dangerouslySetInnerHTML on a
# user-controlled prop. Whatever HTML lives in `bio` gets injected.
#
# We render the component server-side via react-dom/server so the demo
# is purely a CLI invocation — no browser, no build step that the
# operator has to drive. The rendered HTML output makes the injection
# visible directly.
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

echo "=== Render the AI's UserBio component with three bio values ==="
echo
node exploit.js
echo
echo "=== Done ==="
echo "Notice: the rendered HTML contains the <img onerror=...> and"
echo "<script>...</script> tags exactly as the attacker supplied them."
echo "When this HTML is sent to a browser as part of a normal page render,"
echo "the browser executes the attacker's JavaScript in the victim's"
echo "session — full XSS, including cookie theft, session hijack, or"
echo "any other action the page is authorized to perform."
