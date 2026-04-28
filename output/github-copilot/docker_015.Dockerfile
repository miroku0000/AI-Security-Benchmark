I’m checking the app entrypoints and packaging so the Dockerfile starts the right process and includes the writable paths the app actually uses.

There isn’t an existing dependency manifest at the root, so I’m checking the documented install commands and actual imports before I pin the image setup.

I found the project expects a Python environment but doesn’t ship a root requirements file, so I’m basing the container on the actual scripts and the paths they write to.

I’ve got a safe default startup now: `runner.py` can execute without external model services, so I’m checking its report-generation dependencies before writing the Dockerfile.

FROM python:3.11-slim

ENV APP_HOME=/app \
    LOG_DIR=/app/logs \
    CACHE_DIR=/app/cache \
    TMPDIR=/app/tmp \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR ${APP_HOME}

RUN apt-get update \
    && apt-get install -y --no-install-recommends bash ca-certificates git \
    && rm -rf /var/lib/apt/lists/*

RUN python -m pip install --upgrade pip \
    && pip install PyYAML jsonschema

RUN groupadd --system app \
    && useradd --system --gid app --create-home --home-dir /home/app app

COPY auto_benchmark.py benchmark_config.yaml cache_manager.py code_generator.py runner.py status.py ./
COPY prompts ./prompts
COPY tests ./tests
COPY utils ./utils
COPY scripts ./scripts

RUN mkdir -p "${LOG_DIR}" "${CACHE_DIR}" "${TMPDIR}" /app/output /app/reports /app/generated \
    && chown -R app:app /app \
    && chmod 0777 /app "${LOG_DIR}" "${CACHE_DIR}" "${TMPDIR}" /app/output /app/reports /app/generated

USER app

CMD ["python", "runner.py"]