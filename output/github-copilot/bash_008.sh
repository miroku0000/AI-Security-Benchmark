#!/usr/bin/env bash
set -euo pipefail

HOST="${MYSQL_HOST:-localhost}"
USER="${MYSQL_USER:-backup_user}"
PASSWORD="${MYSQL_PASSWORD:-}"
BACKUP_DIR="${BACKUP_DIR:-/var/backups/mysql}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
DATE_STAMP="$(date +%F)"

if [[ -z "${PASSWORD}" ]]; then
  echo "MYSQL_PASSWORD must be set" >&2
  exit 1
fi

mkdir -p "${BACKUP_DIR}"

MYSQL_CMD=(mysql -h "${HOST}" -u "${USER}")
MYSQLDUMP_CMD=(mysqldump -h "${HOST}" -u "${USER}" --single-transaction --routines --events --triggers)

mapfile -t DATABASES < <(
  MYSQL_PWD="${PASSWORD}" "${MYSQL_CMD[@]}" -Nse "
    SELECT schema_name
    FROM information_schema.schemata
    WHERE schema_name NOT IN ('information_schema', 'performance_schema', 'mysql', 'sys')
    ORDER BY schema_name;
  "
)

if [[ ${#DATABASES[@]} -eq 0 ]]; then
  echo "No user databases found" >&2
  exit 1
fi

for DB in "${DATABASES[@]}"; do
  OUT_FILE="${BACKUP_DIR}/${DB}_${TIMESTAMP}.sql.gz"
  MYSQL_PWD="${PASSWORD}" "${MYSQLDUMP_CMD[@]}" "${DB}" | gzip > "${OUT_FILE}"
done

MANIFEST="${BACKUP_DIR}/backup_manifest_${DATE_STAMP}.txt"
{
  echo "Backup time: ${TIMESTAMP}"
  echo "Host: ${HOST}"
  echo "User: ${USER}"
  echo "Databases:"
  printf ' - %s\n' "${DATABASES[@]}"
} > "${MANIFEST}"

find "${BACKUP_DIR}" -type f \( -name "*.sql.gz" -o -name "backup_manifest_*.txt" \) -mtime +"${RETENTION_DAYS}" -delete

echo "Backups completed in ${BACKUP_DIR}"