FROM python:2.7.18-slim-buster

ENV APP_HOME=/opt/app \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PATH=/opt/venv/bin:$PATH

WORKDIR ${APP_HOME}

RUN set -eux; \
    groupadd --system app; \
    useradd --system --gid app --home-dir "${APP_HOME}" --create-home --shell /usr/sbin/nologin app; \
    python -m pip install --no-cache-dir --upgrade "pip==20.3.4" "setuptools==44.1.1" "wheel==0.37.1" "virtualenv==16.7.12"; \
    virtualenv /opt/venv; \
    /opt/venv/bin/pip install --no-cache-dir --upgrade "pip==20.3.4" "setuptools==44.1.1" "wheel==0.37.1"; \
    chown -R app:app /opt/venv "${APP_HOME}"

COPY --chown=app:app . ${APP_HOME}

RUN set -eux; \
    if [ -f requirements.txt ]; then /opt/venv/bin/pip install --no-cache-dir -r requirements.txt; fi; \
    find "${APP_HOME}" -type d -exec chmod 0750 {} \; ; \
    find "${APP_HOME}" -type f -exec chmod 0640 {} \; ; \
    chmod 0750 "${APP_HOME}"

USER app

CMD ["sh", "-c", "if [ -f app.py ]; then exec python app.py; else exec python; fi"]