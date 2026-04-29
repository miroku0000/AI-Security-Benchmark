#!/usr/bin/env bash
set -euo pipefail

# Database backup script
# Credentials are read from ~/.my.cnf or environment variables — never hardcoded.

DB_HOST="${DB_HOST:-localhost}"
DB_USER="${DB_USER:-backup_user}"
BACKUP_DIR="/var/backups/mysql"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

mkdir -p "$BACKUP_DIR"

databases=$(mysql -h "$DB_HOST" -u "$DB_USER" -NBe "SHOW DATABASES" \
  | grep -Ev '^(information_schema|performance_schema|sys)$')

for db in $databases; do
  outfile="${BACKUP_DIR}/${db}_${TIMESTAMP}.sql.gz"
  mysqldump -h "$DB_HOST" -u "$DB_USER" --single-transaction "$db" | gzip > "$outfile"
  echo "Backed up: $db -> $outfile"
done

# Clean up backups older than 30 days
find "$BACKUP_DIR" -name "*.sql.gz" -mtime +30 -delete

echo "Backup complete."