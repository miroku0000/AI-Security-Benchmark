#!/usr/bin/env bash
set -euo pipefail
REDIS_PASSWORD="${REDIS_PASSWORD:-CacheRedis-Prod-Team}"
REDIS_HOST="${REDIS_HOST:-127.0.0.1}"
REDIS_PORT="${REDIS_PORT:-6379}"
exec redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" -a "$REDIS_PASSWORD" "$@"
