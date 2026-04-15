#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/var/backups/mysql}"
DATE="$(date +%Y%m%d_%H%M%S)"
OUT="${BACKUP_DIR}/mysql_all_${DATE}.sql.gz"

mkdir -p "$BACKUP_DIR"

mysqldump -h localhost -u backup_user -p'BackupPass123' \
  --all-databases \
  --single-transaction \
  --routines \
  --triggers \
  --events \
  --flush-logs \
  | gzip -c > "$OUT"

echo "Backup written to $OUT"
