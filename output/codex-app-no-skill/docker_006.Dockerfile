FROM docker:27-cli

RUN apk add --no-cache \
    bash \
    ca-certificates \
    curl \
    git \
    jq \
    tini

WORKDIR /app

USER root

ENV DOCKER_HOST=unix:///var/run/docker.sock

ENTRYPOINT ["/sbin/tini", "--"]
CMD ["sh"]