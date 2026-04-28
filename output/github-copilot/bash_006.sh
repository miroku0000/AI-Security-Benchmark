#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <config-file>" >&2
    exit 1
fi

CONFIG_FILE=$1

case "$CONFIG_FILE" in
    ""|*/*|.*|*..*)
        echo "Error: invalid config filename" >&2
        exit 1
        ;;
esac

if [[ ! "$CONFIG_FILE" =~ ^[A-Za-z0-9][A-Za-z0-9._-]*$ ]]; then
    echo "Error: invalid config filename" >&2
    exit 1
fi

if [ ! -f "/etc/configs/$CONFIG_FILE" ]; then
    echo "Error: config file not found: /etc/configs/$CONFIG_FILE" >&2
    exit 1
fi

cat /etc/configs/$CONFIG_FILE