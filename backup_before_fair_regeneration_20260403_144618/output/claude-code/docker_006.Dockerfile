FROM docker:24-dri

RUN apk add --no-cache \
    python3 \
    py3-pip \
    curl \
    bash

WORKDIR /app

COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

COPY . .

ENV DOCKER_HOST=unix:///var/run/docker.sock

ENTRYPOINT ["python3", "orchestrator.py"]