#!/usr/bin/env bash
set -euo pipefail

SERVICE_NAME="${1:-${SERVICE_NAME:-}}"

if [[ -z "$SERVICE_NAME" ]]; then
  echo "Usage: $0 <service-name>"
  echo "Or set SERVICE_NAME in the environment."
  exit 2
fi

if [[ ! "$SERVICE_NAME" =~ ^[A-Za-z0-9_.@:-]+(\.service)?$ ]]; then
  echo "Invalid service name: $SERVICE_NAME" >&2
  exit 2
fi

if ! command -v systemctl >/dev/null 2>&1; then
  echo "systemctl not found" >&2
  exit 127
fi

if systemctl is-active --quiet "$SERVICE_NAME"; then
  echo "Service '$SERVICE_NAME' is running."
  exit 0
fi

echo "Service '$SERVICE_NAME' is not running."
systemctl status "$SERVICE_NAME" --no-pager || true
exit 1