#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

removed=0
if [ -d __pycache__ ]; then
    rm -rf __pycache__
    echo "  removed __pycache__/"
    removed=$((removed + 1))
fi
if [ -f /tmp/oauth_state_server.log ]; then
    rm -f /tmp/oauth_state_server.log
    echo "  removed /tmp/oauth_state_server.log"
    removed=$((removed + 1))
fi

if [ "$removed" -eq 0 ]; then
    echo "  already clean"
fi
