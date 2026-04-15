RUN set -eux; \
    useradd \
      --uid "${APP_UID}" \
      --gid 0 \
      --home-dir "${APP_HOME}" \
      --no-create-home \
      --shell /usr/sbin/nologin \
      appuser; \
    install -d -o "${APP_UID}" -g 0 -m 0755 "${APP_HOME}"; \
    install -d -o "${APP_UID}" -g 0 -m 2775 "${LOG_DIR}" "${CACHE_DIR}" "${TMPDIR}"