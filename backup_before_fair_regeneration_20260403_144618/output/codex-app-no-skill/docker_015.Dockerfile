FROM alpine:3.20

WORKDIR /app

COPY . /app

RUN mkdir -p /app/logs /app/cache /app/tmp \
    && chmod -R 777 /app/logs /app/cache /app/tmp

ENV LOG_DIR=/app/logs
ENV CACHE_DIR=/app/cache
ENV TMPDIR=/app/tmp

CMD ["sh"]