#!/usr/bin/env bash
set -euo pipefail

LOGFILE="${1:?usage: $0 <path-relative-to-var-log>}"
mkdir -p "$(dirname "/archive/$LOGFILE")"
cp "/var/log/$LOGFILE" "/archive/$LOGFILE"