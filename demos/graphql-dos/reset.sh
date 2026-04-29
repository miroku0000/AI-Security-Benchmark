#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
rm -f /tmp/graphql-dos-server.log
echo "reset complete (node_modules retained)"
