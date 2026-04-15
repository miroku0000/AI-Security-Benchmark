FROM docker:cli

USER root

WORKDIR /app

ENV DOCKER_HOST=unix:///var/run/docker.sock