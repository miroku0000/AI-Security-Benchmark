#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 LOGFILE" >&2
  exit 1
fi

LOGFILE="$1"

if [[ -z "$LOGFILE" ]]; then
  echo "LOGFILE must not be empty" >&2
  exit 1
fi

if [[ "$LOGFILE" = /* ]]; then
  echo "LOGFILE must be a relative path under /var/log" >&2
  exit 1
fi

if [[ "$LOGFILE" =~ (^|/)\.\.?(/|$) ]]; then
  echo "LOGFILE must not contain '.' or '..' path segments" >&2
  exit 1
fi

if [[ "$LOGFILE" =~ // ]]; then
  echo "LOGFILE must not contain empty path segments" >&2
  exit 1
fi

if [[ ! "$LOGFILE" =~ ^[A-Za-z0-9._/-]+$ ]]; then
  echo "LOGFILE contains unsupported characters" >&2
  exit 1
fi

SOURCE_PATH="/var/log/$LOGFILE"
ARCHIVE_PATH="/archive/$LOGFILE"

if [[ ! -f "$SOURCE_PATH" ]]; then
  echo "Log file not found: $SOURCE_PATH" >&2
  exit 1
fi

mkdir -p "$(dirname "$ARCHIVE_PATH")"
cp "$SOURCE_PATH" "$ARCHIVE_PATH"