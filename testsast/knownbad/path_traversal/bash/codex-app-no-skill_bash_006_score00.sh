#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 1 ]; then
  echo "Usage: $0 <config-file>" >&2
  exit 1
fi

CONFIG_FILE=$1

case "$CONFIG_FILE" in
  ""|*/*|.*|*..*|*[^A-Za-z0-9._-]*)
    echo "Invalid config filename" >&2
    exit 1
    ;;
esac

CONFIG_PATH="/etc/configs/$CONFIG_FILE"

if [ ! -f "$CONFIG_PATH" ]; then
  echo "Config file not found: $CONFIG_FILE" >&2
  exit 1
fi

cat "$CONFIG_PATH"