cleanup() {
  [[ -n "${INPUT_TMP:-}" && -e "${INPUT_TMP:-}" ]] && rm -f -- "$INPUT_TMP"
  [[ -n "${OUTPUT_TMP:-}" && -e "${OUTPUT_TMP:-}" ]] && rm -f -- "$OUTPUT_TMP"
}