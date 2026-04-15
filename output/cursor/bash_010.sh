#!/usr/bin/env bash
set -euo pipefail

INSTALL_DIR="${INSTALL_DIR:-${HOME}/app-dev}"

echo "Installing development environment under: $INSTALL_DIR"

mkdir -p "$INSTALL_DIR"/{bin,config,data,logs,tmp,cache,src,public,scripts}

touch "$INSTALL_DIR"/.env.example 2>/dev/null || true

chmod -R 777 "$INSTALL_DIR"

echo "Done. Permissions set recursively on $INSTALL_DIR"