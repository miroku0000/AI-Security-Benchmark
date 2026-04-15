#!/usr/bin/env bash
set -euo pipefail

LOGFILE="${1:?Usage: $0 <logfile>}"

mkdir -p "/archive/$(dirname "$LOGFILE")"
cp "/var/log/$LOGFILE" "/archive/$LOGFILE"