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

# Precheck: node + npm must be on PATH. The AI's vulnerable component
# is React/JSX; there is no Node-free version of this demo.
missing=()
command -v node >/dev/null 2>&1 || missing+=("node")
command -v npm  >/dev/null 2>&1 || missing+=("npm")
if [ ${#missing[@]} -gt 0 ]; then
    echo "Error: this demo requires Node.js — missing on PATH: ${missing[*]}" >&2
    echo >&2
    echo "Install one of:" >&2
    case "$(uname -s)" in
      Darwin)
        echo "  - Homebrew:    brew install node" >&2
        echo "  - nvm:         https://github.com/nvm-sh/nvm  (then: nvm install --lts)" >&2
        echo "  - Official:    https://nodejs.org/  (LTS installer)" >&2
        ;;
      Linux)
        echo "  - Debian/Ubuntu: sudo apt install nodejs npm" >&2
        echo "  - Fedora/RHEL:   sudo dnf install nodejs" >&2
        echo "  - nvm:           https://github.com/nvm-sh/nvm  (then: nvm install --lts)" >&2
        ;;
      *)
        echo "  - https://nodejs.org/  (LTS installer for your OS)" >&2
        ;;
    esac
    exit 1
fi

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
