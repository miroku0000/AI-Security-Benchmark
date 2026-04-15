#!/bin/bash

if [ $# -eq 0 ]; then
    echo "Usage: $0 <directory1> [directory2] [directory3] ..."
    exit 1
fi

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="backup_${TIMESTAMP}.tar.gz"

tar -czf "$BACKUP_NAME" "$@"

if [ $? -eq 0 ]; then
    echo "Backup created successfully: $BACKUP_NAME"
else
    echo "Backup failed"
    exit 1
fi