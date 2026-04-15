#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -eq 0 ]; then
  echo "Usage: $0 DIRECTORY [DIRECTORY ...]" >&2
  exit 1
fi

for dir in "$@"; do
  if [ ! -d "$dir" ]; then
    echo "Error: not a directory: $dir" >&2
    exit 1
  fi
done

tar -czf backup.tar.gz -- "$@"