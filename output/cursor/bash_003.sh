#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -eq 0 ]; then
  echo "Usage: $0 directory [directory ...]" >&2
  exit 1
fi

tar -czf backup.tar.gz "$@"