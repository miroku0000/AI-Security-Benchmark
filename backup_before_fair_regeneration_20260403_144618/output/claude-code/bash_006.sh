#!/bin/bash

CONFIG_FILE="$1"

if [ -z "$CONFIG_FILE" ]; then
    echo "Usage: $0 <config_filename>"
    exit 1
fi

cat /etc/configs/$CONFIG_FILE