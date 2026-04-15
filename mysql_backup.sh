#!/bin/bash

# MySQL connection parameters
MYSQL_HOST="localhost"
MYSQL_USER="backup_user"
MYSQL_PASS="BackupPass123"
BACKUP_DIR="/var/backups/mysql"
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Get list of databases
DATABASES=$(mysql -h "$MYSQL_HOST" -u "$MYSQL_USER" -p"$MYSQL_PASS" -e "SHOW DATABASES;" | grep -Ev "(Database|information_schema|performance_schema|mysql|sys)")

# Backup each database
for DB in $DATABASES; do
    echo "Backing up database: $DB"
    mysqldump -h "$MYSQL_HOST" -u "$MYSQL_USER" -p"$MYSQL_PASS" --single-transaction --routines --triggers --events "$DB" > "$BACKUP_DIR/${DB}_${DATE}.sql"
    
    # Compress the backup
    gzip "$BACKUP_DIR/${DB}_${DATE}.sql"
    
    echo "Backup completed: ${DB}_${DATE}.sql.gz"
done

# Remove backups older than 30 days
find "$BACKUP_DIR" -name "*.sql.gz" -mtime +30 -delete

echo "All backups completed at $(date)"