#!/usr/bin/env bash
# bootstrap-jwt-tool.sh — ensure jwt_tool is cloned and its deps are
# installed in the project venv. Idempotent.
#
# Sourced or run by jwt_001/run-demo.sh and jwt_002/run-demo.sh before
# they call ../crack-and-forge.sh, so end users only need to run one
# script. The clone target ($HOME/tools/jwt_tool) and the venv path
# match the defaults in crack-and-forge.sh.

set -euo pipefail

JWT_TOOL_DIR="${JWT_TOOL_DIR:-$HOME/tools/jwt_tool}"
JWT_TOOL_PY="$JWT_TOOL_DIR/jwt_tool.py"
JWT_TOOL_REPO="https://github.com/ticarpi/jwt_tool"

# Resolve the project venv (../../venv from this script).
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
VENV_PYTHON="${VENV_PYTHON:-$REPO_ROOT/venv/bin/python}"

if [ ! -x "$VENV_PYTHON" ]; then
    echo "Error: project venv python not found at $VENV_PYTHON" >&2
    echo "  Create it: python3 -m venv $REPO_ROOT/venv" >&2
    exit 1
fi

# Clone jwt_tool if missing.
if [ ! -f "$JWT_TOOL_PY" ]; then
    echo "=== One-time: cloning jwt_tool to $JWT_TOOL_DIR ==="
    mkdir -p "$(dirname "$JWT_TOOL_DIR")"
    git clone --depth 1 "$JWT_TOOL_REPO" "$JWT_TOOL_DIR"
    echo
fi

# Install jwt_tool's deps into the project venv if its imports fail.
# jwt_tool requires: termcolor, pycryptodomex, requests.
if ! "$VENV_PYTHON" -c "import termcolor, Cryptodome, requests" >/dev/null 2>&1; then
    echo "=== One-time: installing jwt_tool's deps into project venv ==="
    "$VENV_PYTHON" -m pip install -q -r "$JWT_TOOL_DIR/requirements.txt"
    echo "  ok"
    echo
fi
