#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

readonly CONFIG_DIR='/etc/configs'

usage() {
  printf 'Usage: %s <config-filename>\n' "${0##*/}" >&2
  exit 1
}

die() {
  printf 'Error: %s\n' "$1" >&2
  exit 1
}

[[ $# -eq 1 ]] || usage

CONFIG_FILE=$1

[[ -n "$CONFIG_FILE" ]] || die 'config filename must not be empty'
[[ "$CONFIG_FILE" != *$'\0'* ]] || die 'invalid filename'
[[ "$CONFIG_FILE" != */* ]] || die 'path separators are not allowed'
[[ "$CONFIG_FILE" != '.' && "$CONFIG_FILE" != '..' ]] || die 'invalid filename'
[[ "$CONFIG_FILE" =~ ^[A-Za-z0-9._-]+$ ]] || die 'filename contains invalid characters'

TARGET_PATH="${CONFIG_DIR}/${CONFIG_FILE}"

[[ -d "$CONFIG_DIR" ]] || die 'config directory does not exist'
[[ -e "$TARGET_PATH" ]] || die 'config file does not exist'
[[ -f "$TARGET_PATH" ]] || die 'config path is not a regular file'
[[ ! -L "$TARGET_PATH" ]] || die 'symlinks are not allowed'

if command -v readlink >/dev/null 2>&1; then
  CANONICAL_DIR=$(readlink -f -- "$CONFIG_DIR") || die 'failed to resolve config directory'
  CANONICAL_PATH=$(readlink -f -- "$TARGET_PATH") || die 'failed to resolve config file'
  [[ "$CANONICAL_PATH" == "$CANONICAL_DIR"/* ]] || die 'resolved path escapes config directory'
fi

cat -- "$TARGET_PATH"