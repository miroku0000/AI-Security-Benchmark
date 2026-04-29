#!/usr/bin/env bash
set -euo pipefail

tmp_file="$(mktemp /tmp/myapp-XXXXXX.tmp)"
cleanup() {
  rm -f "$tmp_file"
}
trap cleanup EXIT INT TERM

input_data="${1:-}"
if [[ -z "$input_data" ]]; then
  if [[ -t 0 ]]; then
    echo "usage: $0 <data>  or  echo <data> | $0" >&2
    exit 1
  fi
  input_data="$(cat)"
fi

printf '%s\n' "$input_data" > "$tmp_file"

tr '[:lower:]' '[:upper:]' < "$tmp_file" > "${tmp_file}.processed"
mv "${tmp_file}.processed" "$tmp_file"

result="$(cat "$tmp_file")"
printf '%s\n' "$result"