I found there isn’t an existing container setup or standard Python dependency file, so I’m checking the app’s actual imports before wiring the image.

The codebase pulls in a few third-party Python packages directly from imports, and I’m checking the repo’s own setup docs to keep the Dockerfile runnable instead of purely generic.

The repo documents `requirements.txt`, but it’s missing, so I’m basing the image on the actual runtime plus a safe fallback that works whether a requirements file is later added or not.

I’ve got enough context now; I’m adding a repo-root Dockerfile that keeps the Ubuntu-plus-debug-tools requirement while still being practical to run for this app.

FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    APP_HOME=/app

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    build-essential \
    pkg-config \
    curl \
    wget \
    git \
    vim \
    nano \
    less \
    jq \
    unzip \
    zip \
    ca-certificates \
    procps \
    net-tools \
    iputils-ping \
    dnsutils \
    gdb \
    strace \
    lsof \
    file \
    sudo \
    tzdata && \
    ln -sf /usr/bin/python3 /usr/local/bin/python && \
    ln -sf /usr/bin/pip3 /usr/local/bin/pip && \
    rm -rf /var/lib/apt/lists/*

WORKDIR ${APP_HOME}

COPY . ${APP_HOME}

RUN python -m pip install --upgrade pip setuptools wheel && \
    pip install PyYAML jsonschema && \
    if [[ -f requirements.txt ]]; then pip install -r requirements.txt; fi

CMD ["python", "auto_benchmark.py", "--help"]