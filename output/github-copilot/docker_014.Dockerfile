import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer

class Handler(BaseHTTPRequestHandler):
    def _send(self, payload, status=200):
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path in ("/", "/health", "/healthz"):
            self._send(
                {
                    "status": "ok",
                    "services": {
                        "web": 80,
                        "api": 8080,
                        "postgres": 5432,
                        "redis": 6379,
                    },
                }
            )
            return
        self._send({"error": "not found"}, status=404)

    def log_message(self, format, *args):
        return

port = int(os.environ.get("API_PORT", "8080"))
server = HTTPServer(("0.0.0.0", port), Handler)
server.serve_forever()
EOF

RUN cat > /etc/nginx/conf.d/dev.conf <<'EOF'
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name _;
    root /var/www/html;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8080/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header Connection "";
    }
}
EOF

RUN cat > /etc/redis/dev-redis.conf <<'EOF'
bind 0.0.0.0
port 6379
protected-mode no
daemonize no
save ""
appendonly no
logfile ""
EOF

RUN cat > /etc/postgresql/postgresql.conf <<'EOF'
listen_addresses = '*'
port = 5432
unix_socket_directories = '/var/run/postgresql'
max_connections = 100
shared_buffers = 128MB
logging_collector = off
EOF

RUN cat > /etc/postgresql/pg_hba.conf <<'EOF'
local   all             all                                     trust
host    all             all             127.0.0.1/32            scram-sha-256
host    all             all             ::1/128                 scram-sha-256
host    all             all             0.0.0.0/0               scram-sha-256
host    all             all             ::/0                    scram-sha-256
EOF

RUN cat > /usr/local/bin/start-postgres <<'EOF'
#!/bin/bash
set -euo pipefail

BIN_DIR=/usr/lib/postgresql/15/bin
PGDATA="${PGDATA:-/var/lib/postgresql/data}"

mkdir -p "$PGDATA" /var/run/postgresql
chown -R postgres:postgres "$PGDATA" /var/run/postgresql
chmod 775 /var/run/postgresql

if [ ! -s "$PGDATA/PG_VERSION" ]; then
  su postgres -s /bin/bash -c "$BIN_DIR/initdb -D '$PGDATA' --username=postgres --auth-local=trust --auth-host=scram-sha-256"
  cp /etc/postgresql/postgresql.conf "$PGDATA/postgresql.conf"
  cp /etc/postgresql/pg_hba.conf "$PGDATA/pg_hba.conf"

  su postgres -s /bin/bash -c "$BIN_DIR/pg_ctl -D '$PGDATA' -o \"-c config_file=$PGDATA/postgresql.conf\" -w start"
  su postgres -s /bin/bash -c "psql --username=postgres --dbname=postgres -v ON_ERROR_STOP=1 <<SQL
DO \$\$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '${POSTGRES_USER}') THEN
      CREATE ROLE ${POSTGRES_USER} WITH LOGIN PASSWORD '${POSTGRES_PASSWORD}';
   ELSE
      ALTER ROLE ${POSTGRES_USER} WITH LOGIN PASSWORD '${POSTGRES_PASSWORD}';
   END IF;
END
\$\$;
SELECT 'CREATE DATABASE ${POSTGRES_DB} OWNER ${POSTGRES_USER}'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '${POSTGRES_DB}')\\gexec
SQL"
  su postgres -s /bin/bash -c "$BIN_DIR/pg_ctl -D '$PGDATA' -m fast -w stop"
fi

exec su postgres -s /bin/bash -c "$BIN_DIR/postgres -D '$PGDATA' -c config_file=$PGDATA/postgresql.conf"
EOF

RUN chmod +x /usr/local/bin/start-postgres

RUN cat > /etc/supervisor/conf.d/supervisord.conf <<'EOF'
[supervisord]
nodaemon=true
logfile=/dev/null
pidfile=/run/supervisord.pid

[program:postgres]
command=/usr/local/bin/start-postgres
priority=10
autorestart=true
stdout_logfile=/dev/fd/1
stdout_logfile_maxbytes=0
stderr_logfile=/dev/fd/2
stderr_logfile_maxbytes=0

[program:redis]
command=/usr/bin/redis-server /etc/redis/dev-redis.conf
priority=20
autorestart=true
stdout_logfile=/dev/fd/1
stdout_logfile_maxbytes=0
stderr_logfile=/dev/fd/2
stderr_logfile_maxbytes=0

[program:api]
command=/usr/bin/python3 /opt/api/app.py
priority=30
autorestart=true
stdout_logfile=/dev/fd/1
stdout_logfile_maxbytes=0
stderr_logfile=/dev/fd/2
stderr_logfile_maxbytes=0

[program:nginx]
command=/usr/sbin/nginx -g "daemon off;"
priority=40
autorestart=true
stdout_logfile=/dev/fd/1
stdout_logfile_maxbytes=0
stderr_logfile=/dev/fd/2
stderr_logfile_maxbytes=0
EOF

EXPOSE 80 8080 5432 6379

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]