#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

removed=0
if [ -d __pycache__ ]; then
    rm -rf __pycache__
    echo "  removed __pycache__/"
    removed=$((removed + 1))
fi
if [ -f /tmp/ssrf_file_read_imds.log ]; then
    rm -f /tmp/ssrf_file_read_imds.log
    echo "  removed /tmp/ssrf_file_read_imds.log"
    removed=$((removed + 1))
fi
if [ -f /tmp/ssrf-file-read-demo-fake-secret.txt ]; then
    rm -f /tmp/ssrf-file-read-demo-fake-secret.txt
    echo "  removed /tmp/ssrf-file-read-demo-fake-secret.txt"
    removed=$((removed + 1))
fi

if [ "$removed" -eq 0 ]; then
    echo "  already clean"
fi
