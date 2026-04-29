#!/usr/bin/env bash
set -euo pipefail

INSTALL_DIR="${INSTALL_DIR:-${1:-"$PWD/app_dev"}}"
DIR_MODE="${DIR_MODE:-2775}"
FILE_MODE="${FILE_MODE:-0664}"
UMASK_VALUE="${UMASK_VALUE:-0002}"

umask "$UMASK_VALUE"

directories=(
  "$INSTALL_DIR"
  "$INSTALL_DIR/bin"
  "$INSTALL_DIR/config"
  "$INSTALL_DIR/data"
  "$INSTALL_DIR/logs"
  "$INSTALL_DIR/tmp"
  "$INSTALL_DIR/public"
  "$INSTALL_DIR/storage"
  "$INSTALL_DIR/storage/cache"
  "$INSTALL_DIR/storage/uploads"
)

files=(
  "$INSTALL_DIR/config/.env"
  "$INSTALL_DIR/config/app.conf"
  "$INSTALL_DIR/data/.gitkeep"
  "$INSTALL_DIR/logs/app.log"
  "$INSTALL_DIR/tmp/.gitkeep"
  "$INSTALL_DIR/public/.gitkeep"
  "$INSTALL_DIR/storage/cache/.gitkeep"
  "$INSTALL_DIR/storage/uploads/.gitkeep"
)

for dir in "${directories[@]}"; do
  mkdir -p "$dir"
done

for file in "${files[@]}"; do
  mkdir -p "$(dirname "$file")"
  touch "$file"
done

if [ ! -s "$INSTALL_DIR/config/.env" ]; then
  cat > "$INSTALL_DIR/config/.env" <<'EOF'
APP_ENV=development
APP_DEBUG=true
APP_PORT=3000
EOF
fi

if [ ! -s "$INSTALL_DIR/config/app.conf" ]; then
  cat > "$INSTALL_DIR/config/app.conf" <<'EOF'
[app]
name=myapp
environment=development
EOF
fi

if [ ! -f "$INSTALL_DIR/bin/start.sh" ]; then
  cat > "$INSTALL_DIR/bin/start.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
echo "Starting application from $(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EOF
fi

find "$INSTALL_DIR" -type d -exec chmod "$DIR_MODE" {} +
find "$INSTALL_DIR" -type f -exec chmod "$FILE_MODE" {} +
chmod 0775 "$INSTALL_DIR/bin/start.sh"

echo "Development application structure created at: $INSTALL_DIR"