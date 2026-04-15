FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PATH="/opt/venv/bin:${PATH}" \
    PORT=8000

WORKDIR /app

RUN set -eux; \
    python -m venv /opt/venv; \
    groupadd --system app; \
    useradd --system --gid app --create-home --home-dir /home/app --shell /usr/sbin/nologin app

COPY --chown=app:app . /app

RUN set -eux; \
    if [ -f requirements.txt ]; then \
        /opt/venv/bin/pip install --no-cache-dir --requirement requirements.txt; \
    elif [ -f pyproject.toml ]; then \
        /opt/venv/bin/pip install --no-cache-dir .; \
    else \
        echo "No supported dependency manifest found (expected requirements.txt or pyproject.toml)." >&2; \
        exit 1; \
    fi

USER app:app

EXPOSE 8000

CMD PORT="${PORT:-8000}" exec /opt/venv/bin/python /app/app.py "$PORT"