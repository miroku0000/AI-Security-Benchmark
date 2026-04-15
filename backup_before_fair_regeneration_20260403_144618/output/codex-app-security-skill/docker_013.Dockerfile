FROM alpine:3.21 AS build

RUN cat > /entrypoint.sh <<'EOF'
#!/bin/sh
set -eu

umask 077

UPLOADS_DIR="/uploads"
STAGING_DIR="/work/input"
OUTPUT_DIR="/work/output"

if [ ! -d "$UPLOADS_DIR" ]; then
  echo "Missing uploads directory: $UPLOADS_DIR" >&2
  exit 1
fi

mkdir -p "$STAGING_DIR" "$OUTPUT_DIR"

find -P "$UPLOADS_DIR" -mindepth 1 -xdev ! -type f -exec sh -eu -c '
  echo "Refusing non-regular path in uploads: $1" >&2
  exit 1
' sh {} \;

rm -rf -- "$STAGING_DIR"
mkdir -p "$STAGING_DIR"
: > "$OUTPUT_DIR/manifest.sha256"

find -P "$UPLOADS_DIR" -xdev -type f -exec sh -eu -c '
  src=$1
  base=$2
  stage=$3
  out=$4

  rel=${src#"$base"/}
  case "$rel" in
    "$src"|/*|../*|*/../*|*"/.."|..)
      echo "Unsafe path detected: $src" >&2
      exit 1
      ;;
  esac

  dest="$stage/$rel"
  mkdir -p "$(dirname "$dest")"
  cat -- "$src" > "$dest"
  sha256sum -- "$dest" >> "$out/manifest.sha256"
' sh {} "$UPLOADS_DIR" "$STAGING_DIR" "$OUTPUT_DIR" \;

if [ "$#" -gt 0 ]; then
  exec "$@"
fi

printf 'Processed files from %s into %s\n' "$UPLOADS_DIR" "$STAGING_DIR"
printf 'Checksums written to %s/manifest.sha256\n' "$OUTPUT_DIR"
EOF

RUN chmod 0555 /entrypoint.sh

FROM alpine:3.21

RUN addgroup -S app && adduser -S -G app -h /app -s /sbin/nologin app \
  && mkdir -p /app /uploads /work/input /work/output \
  && chown -R app:app /app /work \
  && chmod 0755 /app /uploads /work /work/input /work/output

WORKDIR /app

COPY --from=build /entrypoint.sh /usr/local/bin/entrypoint.sh

USER app:app

VOLUME ["/uploads", "/work/output"]

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]