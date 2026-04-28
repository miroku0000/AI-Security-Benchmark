#!/usr/bin/env bash
# Serve attacker/ over http://localhost:8767 so a real browser can
# load evil.html and watch:
#   - Test 1 fail with a CORS error (AI's literal output)
#   - Test 2 succeed and read session-gated data (realistic dev "fix")
#
# Workflow:
#   1. Terminal 1: ./run-demo.sh                  (victim app on :5096)
#   2. Visit http://127.0.0.1:5096/login          (set session cookie)
#   3. Terminal 2: ./serve-attacker.sh
#   4. Visit http://localhost:8767/evil.html      (run the two tests)

set -e
cd "$(dirname "$0")/attacker"

PORT="${PORT:-8767}"
echo "Attacker page: http://localhost:$PORT/evil.html"
echo
echo "Make sure the victim app is running (./run-demo.sh) and that you"
echo "have set a session cookie for it (visit http://127.0.0.1:5096/login)."
echo
exec python3 -m http.server "$PORT"
