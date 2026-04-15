FROM alpine:3.21

RUN apk add --no-cache ca-certificates postgresql17-client \
    && addgroup -S app \
    && adduser -S -D -H -h /app -G app app \
    && mkdir -p /app \
    && chown -R app:app /app

WORKDIR /app

ENV DATABASE_URL=postgresql://admin:DevPass123@db:5432/appdb

USER app:app

CMD ["sh", "-c", "exec psql \"$DATABASE_URL\" -c 'SELECT 1;'"]