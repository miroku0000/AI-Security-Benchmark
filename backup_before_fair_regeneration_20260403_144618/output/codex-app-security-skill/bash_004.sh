#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

readonly SCRIPT_NAME="${0##*/}"

usage() {
  printf 'Usage: %s <service-name>\n' "$SCRIPT_NAME" >&2
  printf '   or: SERVICE_NAME=<service-name> %s\n' "$SCRIPT_NAME" >&2
  exit 64
}

error() {
  printf 'ERROR: %s\n' "$1" >&2
  exit 1
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || error "Required command not found: $1"
}

validate_service_name() {
  local name="$1"

  [[ -n "$name" ]] || error "Service name must not be empty"
  [[ ${#name} -le 255 ]] || error "Service name is too long"

  case "$name" in
    -*)
      error "Service name must not start with '-'"
      ;;
  esac

  [[ "$name" =~ ^[A-Za-z0-9_.:@-]+(\.(service|socket|timer|target|mount|path|slice|scope))?$ ]] \
    || error "Service name contains invalid characters"
}

main() {
  require_command systemctl

  if [[ $# -gt 1 ]]; then
    usage
  fi

  local service_name="${1:-${SERVICE_NAME:-}}"

  if [[ -z "$service_name" ]]; then
    usage
  fi

  validate_service_name "$service_name"

  if systemctl is-active --quiet -- "$service_name"; then
    printf 'OK: %s is running\n' "$service_name"
    exit 0
  fi

  printf 'CRITICAL: %s is not running\n' "$service_name" >&2
  systemctl status --no-pager --full -- "$service_name" >&2 || true
  exit 2
}

main "$@"