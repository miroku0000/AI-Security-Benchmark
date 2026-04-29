#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
rm -f /tmp/node-deserialize-PWND.txt /tmp/node-deserialize-PWND.txt.id /tmp/node-deserialize-server.log
echo "reset complete (node_modules retained)"
