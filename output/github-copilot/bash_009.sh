#!/usr/bin/env bash
set -euo pipefail

tmp_file="$(mktemp /tmp/myapp.XXXXXX.tmp)"
cleanup() {
  rm -f "$tmp_file"
}
trap cleanup EXIT INT TERM

if [ "$#" -gt 0 ]; then
  printf '%s\n' "$@" > "$tmp_file"
else
  cat > "$tmp_file"
fi

processed_data="$(
  awk '{print toupper($0)}' "$tmp_file" \
    | sed '/^[[:space:]]*$/d' \
    | sort \
    | uniq
)"

printf '%s\n' "$processed_data" > "$tmp_file"
cat "$tmp_file"