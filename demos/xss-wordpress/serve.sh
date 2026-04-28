#!/usr/bin/env bash
# Serve the rendered HTML files on http://localhost:8765/ so a browser
# can fetch them and execute the embedded payloads as a real victim
# would.
#
# Run ./run-demo.sh first to generate the files in out/. Then:
#   ./serve.sh
# Then in a browser:
#   http://localhost:8765/legitimate.html
#   http://localhost:8765/alert.html
#   http://localhost:8765/defacement.html
#   http://localhost:8765/cookie-display.html
#
# Ctrl-C to stop.

set -e
cd "$(dirname "$0")"

if [ ! -d out ]; then
    echo "Error: out/ does not exist. Run ./run-demo.sh first to generate it." >&2
    exit 1
fi

PORT="${PORT:-8765}"
echo "Serving demos/xss-wordpress/out/ on http://localhost:$PORT/"
echo "Open in a browser:"
echo "  http://localhost:$PORT/legitimate.html"
echo "  http://localhost:$PORT/alert.html"
echo "  http://localhost:$PORT/defacement.html"
echo "  http://localhost:$PORT/cookie-display.html"
echo
echo "Ctrl-C to stop."
echo
exec python3 -m http.server "$PORT" --directory out --bind 127.0.0.1
