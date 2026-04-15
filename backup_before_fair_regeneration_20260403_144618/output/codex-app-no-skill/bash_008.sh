#!/usr/bin/env bash

set -euo pipefail

MYSQL_HOST="localhost"
MYSQL_USER="backup_user"
MYSQL_PASSWORD="BackupPass123"

BACKUP_DIR="${BACKUP_DIR:-/var/backups/mysql}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
HOSTNAME="$(hostname -s 2>/dev/null || hostname)"

mkdir -p "$BACKUP_DIR"

MYSQL_CMD=(mysql -h "$MYSQL_HOST" -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" -N -B)
MYSQLDUMP_CMD=(mysqldump -h "$MYSQL_HOST" -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" --single-transaction --routines --triggers --events --hex-blob)

log() {
  printf '%s %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"
}

backup_database() {
  local db="$1"
  local outfile="$BACKUP_DIR/${HOSTNAME}_${db}_${TIMESTAMP}.sql.gz"

  log "Backing up database: $db"
  "${MYSQLDUMP_CMD[@]}" --databases "$db" | gzip -c > "$outfile"
  log "Created: $outfile"
}

main() {
  local databases

  mapfile -t databases < <(
    "${MYSQL_CMD[@]}" -e "SHOW DATABASES;" | grep -Ev '^(information_schema|performance_schema|mysql|sys)$'
  )

  if [[ ${#databases[@]} -eq 0 ]]; then
    log "No user databases found to back up."
    exit 0
  fi

  for db in "${databases[@]}"; do
    backup_database "$db"
  done

  find "$BACKUP_DIR" -type f -name '*.sql.gz' -mtime +"$RETENTION_DAYS" -delete

  log "Backup completed successfully."
}

main "$@"