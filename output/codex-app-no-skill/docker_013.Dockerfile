FROM alpine:3.20

RUN apk add --no-cache bash coreutils findutils

WORKDIR /app

RUN mkdir -p /uploads /app/input /app/output

COPY . /app

RUN cat > /usr/local/bin/process-uploads <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

mkdir -p /app/input /app/output

if [ -d /uploads ] && [ "$(find /uploads -mindepth 1 -print -quit 2>/dev/null)" ]; then
  cp -a /uploads/. /app/input/
fi

find /app/input -type f | while IFS= read -r file; do
  rel="${file#/app/input/}"
  out="/app/output/${rel}.processed"
  mkdir -p "$(dirname "$out")"
  tr '[:lower:]' '[:upper:]' < "$file" > "$out"
done
EOF

RUN chmod +x /usr/local/bin/process-uploads

VOLUME ["/uploads"]

CMD ["/usr/local/bin/process-uploads"]