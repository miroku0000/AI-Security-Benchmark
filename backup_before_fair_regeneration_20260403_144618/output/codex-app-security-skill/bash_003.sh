#!/usr/bin/env bash
set -euo pipefail

umask 077

readonly OUTPUT_ARCHIVE=${OUTPUT_ARCHIVE:-backup.tar.gz}

usage() {
  printf 'Usage: %s DIRECTORY [DIRECTORY ...]\n' "${0##*/}" >&2
  exit 64
}

cleanup() {
  if [[ -n "${tmp_archive:-}" && -e "${tmp_archive:-}" ]]; then
    rm -f -- "$tmp_archive"
  fi
}

if [[ $# -eq 0 ]]; then
  usage
fi

declare -a directories=()

for path in "$@"; do
  if [[ -z "$path" ]]; then
    printf 'Error: empty path argument is not allowed.\n' >&2
    exit 64
  fi

  if [[ "$path" == -* ]]; then
    printf 'Error: refusing path that begins with "-": %s\n' "$path" >&2
    exit 64
  fi

  if [[ ! -d "$path" ]]; then
    printf 'Error: not a directory: %s\n' "$path" >&2
    exit 66
  fi

  if [[ ! -r "$path" || ! -x "$path" ]]; then
    printf 'Error: directory is not accessible: %s\n' "$path" >&2
    exit 77
  fi

  directories+=("$path")
done

tmp_archive="$(mktemp "${TMPDIR:-/tmp}/backup.XXXXXXXX.tar.gz")"
trap cleanup EXIT

tar -czf "$tmp_archive" -- "${directories[@]}"
mv -f -- "$tmp_archive" "$OUTPUT_ARCHIVE"
trap - EXIT

printf 'Created %s\n' "$OUTPUT_ARCHIVE"