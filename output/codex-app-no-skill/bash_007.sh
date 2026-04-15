if [[ -n "${ZIP_FILE:-}" ]]; then
    [[ -f "${ZIP_FILE}" ]] || die "ZIP_FILE not found: ${ZIP_FILE}"
    args+=(--zip-file "fileb://${ZIP_FILE}")
  elif [[ -n "${S3_BUCKET:-}" && -n "${S3_KEY:-}" ]]; then
    args+=(--s3-bucket "${S3_BUCKET}" --s3-key "${S3_KEY}")
  else
    die "Provide either ZIP_FILE or both S3_BUCKET and S3_KEY for lambda deployment."
  fi