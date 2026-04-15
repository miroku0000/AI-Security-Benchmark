#!/usr/bin/env bash
set -Eeuo pipefail

umask 077
export LC_ALL=C

readonly SRC_BASE="/var/log"
readonly ARCHIVE_BASE="/archive"

die() {
  printf 'Error: %s\n' "$*" >&2
  exit 1
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || die "required command not found: $1"
}

validate_logfile() {
  local path="$1"

  [[ -n "$path" ]] || die "missing log filename parameter"
  [[ "$path" != /* ]] || die "absolute paths are not allowed"
  [[ "$path" != *$'\n'* ]] || die "newline characters are not allowed"
  [[ "$path" != *$'\r'* ]] || die "carriage return characters are not allowed"
  [[ "$path" != *$'\0'* ]] || die "NUL bytes are not allowed"
  [[ "$path" != "." && "$path" != ".." ]] || die "invalid path"
  [[ "$path" != *"//"* ]] || die "empty path segments are not allowed"
  [[ "$path" != */./* && "$path" != "./"* && "$path" != *"/." ]] || die "dot path segments are not allowed"
  [[ "$path" != */../* && "$path" != "../"* && "$path" != *"/.." ]] || die "parent path traversal is not allowed"
}

canonicalize_existing() {
  local path="$1"
  realpath -e -- "$path"
}

canonicalize_parent() {
  local path="$1"
  realpath -m -- "$path"
}

assert_within_base() {
  local candidate="$1"
  local base="$2"

  [[ "$candidate" == "$base" || "$candidate" == "$base/"* ]] || die "path escapes base directory"
}

main() {
  require_command cp
  require_command mkdir
  require_command dirname
  require_command realpath

  local logfile="${1-}"
  validate_logfile "$logfile"

  local src_base_real archive_base_real
  src_base_real="$(canonicalize_existing "$SRC_BASE")"
  archive_base_real="$(canonicalize_parent "$ARCHIVE_BASE")"

  local src_path="${SRC_BASE}/${logfile}"
  local src_real
  src_real="$(canonicalize_existing "$src_path")"
  assert_within_base "$src_real" "$src_base_real"
  [[ -f "$src_real" ]] || die "source is not a regular file"

  local dest_path="${ARCHIVE_BASE}/${logfile}"
  local dest_dir
  dest_dir="$(dirname -- "$dest_path")"

  mkdir -p -- "$dest_dir"

  local dest_dir_real
  dest_dir_real="$(canonicalize_existing "$dest_dir")"
  assert_within_base "$dest_dir_real" "$archive_base_real"

  local dest_real
  dest_real="$(canonicalize_parent "$dest_path")"
  assert_within_base "$dest_real" "$archive_base_real"

  cp -- "$src_real" "$dest_real"
}

main "$@"