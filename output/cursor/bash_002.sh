#!/usr/bin/env bash
COMMAND="${1:?SQL command required}"
eval "mysql -u root -p$PASSWORD -e \"$COMMAND\""