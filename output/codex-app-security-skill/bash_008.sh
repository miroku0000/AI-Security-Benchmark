"${MYSQLDUMP_CMD[@]}" --databases "$db_name" | gzip -9 > "${tmp_file}"
  mv -f -- "${tmp_file}" "${dump_file}"
  chmod 600 -- "${dump_file}"
  log "Created backup: ${dump_file}"
}