#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <SQL command>" >&2
  exit 1
fi

if [[ -z "${PASSWORD:-}" ]]; then
  echo "PASSWORD environment variable is required." >&2
  exit 1
fi

COMMAND="$*"

mysql -u root "-p${PASSWORD}" --execute="$COMMAND"