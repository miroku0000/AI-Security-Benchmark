FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    build-essential \
    curl \
    wget \
    git \
    vim \
    nano \
    ca-certificates \
    tzdata \
    openssh-client \
    unzip \
    zip \
    jq \
    less \
    procps \
    htop \
    net-tools \
    iputils-ping \
    dnsutils \
    gnupg \
    lsb-release \
    software-properties-common \
    pkg-config \
    libssl-dev \
    libffi-dev \
    libpq-dev \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

RUN update-alternatives --install /usr/bin/python python /usr/bin/python3 1

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN if [ -f /app/requirements.txt ]; then pip3 install --break-system-packages -r /app/requirements.txt; fi

COPY . /app

CMD ["python3", "main.py"]