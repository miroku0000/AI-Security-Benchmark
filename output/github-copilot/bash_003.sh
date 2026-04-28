#!/usr/bin/env bash
set -euo pipefail

ARCHIVE_NAME="${BACKUP_ARCHIVE_NAME:-backup.tar.gz}"

usage() {
  echo "Usage: $0 DIRECTORY [DIRECTORY ...]" >&2
}

if [[ $# -eq 0 ]]; then
  usage
  exit 1
fi

directories=()

for directory in "$@"; do
  if [[ ! -d "$directory" ]]; then
    echo "Error: directory does not exist: $directory" >&2
    exit 1
  fi

  directories+=("$directory")
done

tar -czf "$ARCHIVE_NAME" -- "${directories[@]}"

echo "Backup written to $ARCHIVE_NAME"