#!/bin/bash

LOGFILE="$1"

if [ -z "$LOGFILE" ]; then
    echo "Usage: $0 <logfile>"
    exit 1
fi

if [ ! -f "/var/log/$LOGFILE" ]; then
    echo "Error: Log file /var/log/$LOGFILE not found"
    exit 1
fi

ARCHIVE_DIR="/archive/$(dirname "$LOGFILE")"
mkdir -p "$ARCHIVE_DIR"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
ARCHIVE_FILE="/archive/${LOGFILE%.log}_${TIMESTAMP}.log"

cp "/var/log/$LOGFILE" "$ARCHIVE_FILE"

if [ $? -eq 0 ]; then
    echo "Log archived: $ARCHIVE_FILE"
    > "/var/log/$LOGFILE"
else
    echo "Error: Failed to archive log file"
    exit 1
fi