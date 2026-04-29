#!/usr/bin/env bash
# Serve attacker/ over http://localhost:8766 so a real browser can load
# evil.html and the auto-submit form actually fires cross-origin.
#
# Workflow:
#   1. In one terminal: ./run-demo.sh   (starts the victim app on 3093)
#   2. Visit http://127.0.0.1:3093/login?userId=alice in your browser
#      (sets the session cookie).
#   3. In another terminal: ./serve-attacker.sh
#   4. Visit http://localhost:8766/evil.html — the page auto-submits
#      the cross-origin form and Alice's account gets deleted.
#   5. Visit http://127.0.0.1:3093/deleted to see the log.
#
# Usage:
#   ./serve-attacker.sh

set -e
cd "$(dirname "$0")/attacker"

PORT="${PORT:-8766}"
echo "Serving attacker page at:"
echo "  http://localhost:$PORT/evil.html"
echo
echo "Make sure the victim app is running (./run-demo.sh in another terminal)"
echo "and that you have a session cookie set for http://127.0.0.1:3093"
echo "(visit http://127.0.0.1:3093/login?userId=alice in the same browser)."
echo
exec python3 -m http.server "$PORT" --bind 127.0.0.1
