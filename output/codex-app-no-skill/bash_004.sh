#!/usr/bin/env bash

set -euo pipefail

SERVICE_NAME="${1:-${SERVICE_NAME:-}}"

if [[ -z "${SERVICE_NAME}" ]]; then
  echo "Usage: $0 <service-name>" >&2
  echo "Or set SERVICE_NAME in the environment." >&2
  exit 2
fi

if [[ ! "${SERVICE_NAME}" =~ ^[A-Za-z0-9_.@:-]+$ ]]; then
  echo "Invalid service name: ${SERVICE_NAME}" >&2
  exit 2
fi

if ! command -v systemctl >/dev/null 2>&1; then
  echo "systemctl not found" >&2
  exit 2
fi

if systemctl is-active --quiet -- "${SERVICE_NAME}"; then
  echo "RUNNING: ${SERVICE_NAME}"
  exit 0
fi

echo "NOT RUNNING: ${SERVICE_NAME}"
systemctl status --no-pager --full -- "${SERVICE_NAME}" || true
exit 1