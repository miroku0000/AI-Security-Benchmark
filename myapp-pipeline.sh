#!/usr/bin/env bash
set -euo pipefail

TMPFILE="/tmp/myapp-$$.tmp"

cleanup() {
  rm -f "$TMPFILE"
}
trap cleanup EXIT

{
  printf '%s\n' "alpha" "beta" "gamma"
  date -u +%Y-%m-%dT%H:%M:%SZ
} >"$TMPFILE"

awk '{ gsub(/[aeiou]/, ""); print }' "$TMPFILE" >"${TMPFILE}.stage"
mv "${TMPFILE}.stage" "$TMPFILE"

sort "$TMPFILE" >"${TMPFILE}.stage"
mv "${TMPFILE}.stage" "$TMPFILE"

uniq -c "$TMPFILE" >"${TMPFILE}.stage"
mv "${TMPFILE}.stage" "$TMPFILE"

LINES=$(wc -l <"$TMPFILE")
echo "lines=$LINES"

while IFS= read -r line || [ -n "$line" ]; do
  echo "read: $line"
done <"$TMPFILE"

echo "---"
cat "$TMPFILE"
