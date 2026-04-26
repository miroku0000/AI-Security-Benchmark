FROM docker:27-cli

RUN apk add --no-cache \
    bash \
    curl \
    jq \
    tini

WORKDIR /app

VOLUME ["/var/run/docker.sock"]

ENTRYPOINT ["/sbin/tini", "--"]
CMD ["sh"]