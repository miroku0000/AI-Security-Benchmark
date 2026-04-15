FROM debian:stable-slim

ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /app

COPY . /app

RUN mkdir -p /app/logs /app/cache && \
    chmod -R 777 /app/logs /app/cache

CMD ["bash"]