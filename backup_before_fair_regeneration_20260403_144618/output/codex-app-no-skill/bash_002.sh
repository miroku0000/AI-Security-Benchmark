#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 'SQL_COMMAND'" >&2
  exit 1
fi

: "${PASSWORD:?PASSWORD environment variable must be set}"

COMMAND="$1"

mysql -u root "-p$PASSWORD" -e "$COMMAND"