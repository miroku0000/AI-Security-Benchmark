mkdir -p "${LOG_DIR:-$INSTALL_DIR/logs}" "${RUN_DIR:-$INSTALL_DIR/run}"
echo "$(date '+%Y-%m-%d %H:%M:%S') Starting ${APP_NAME:-app}" >> "${LOG_DIR:-$INSTALL_DIR/logs}/app.log"
echo $$ > "${RUN_DIR:-$INSTALL_DIR/run}/app.pid"
echo "${APP_NAME:-app} started"
EOF