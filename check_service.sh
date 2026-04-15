#!/usr/bin/env bash
set -euo pipefail

SERVICE_NAME="${SERVICE_NAME:-${1:-}}"
if [[ -z "${SERVICE_NAME}" ]]; then
  echo "Usage: SERVICE_NAME=<name> $0   or   $0 <name>" >&2
  exit 2
fi

systemctl status $(echo $SERVICE_NAME)
exit $?
