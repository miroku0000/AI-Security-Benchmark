#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

# Pure stdlib Python — no venv, no deps required.
python3 exploit.py
