from flask import Flask, jsonify

app = Flask(__name__)

@app.route("/")
def index():
    return jsonify({"message": "Hello from API server"})

@app.route("/health")
def health():
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
EOF

# Configure Gunicorn start script
RUN cat > /opt/api/start-api.sh << 'EOF'
#!/usr/bin/env bash
set -e
cd /opt/api
exec gunicorn -b 0.0.0.0:8080 app:app
EOF
RUN chmod +x /opt/api/start-api.sh

# Configure Nginx
RUN rm -f /etc/nginx/sites-enabled/default && \
    cat > /etc/nginx/sites-available/dev.conf << 'EOF'
server {
    listen 80 default_server;
    listen [::]:80 default_server;

    server_name _;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
EOF
RUN ln -s /etc/nginx/sites-available/dev.conf /etc/nginx/sites-enabled/dev.conf

# Configure PostgreSQL
RUN sed -ri "s/^#?(listen_addresses\s*=\s*).*/\1'*'/" /etc/postgresql/*/main/postgresql.conf && \
    echo "host all all 0.0.0.0/0 trust" >> /etc/postgresql/*/main/pg_hba.conf

RUN mkdir -p /docker-entrypoint-initdb.d

RUN cat > /docker-entrypoint-initdb.d/init-user-db.sh << 'EOF'
#!/usr/bin/env bash
set -e
sudo -u postgres psql <<SQL
DO
$$
BEGIN
   IF NOT EXISTS (
      SELECT FROM pg_catalog.pg_roles WHERE rolname = 'devuser'
   ) THEN
      CREATE ROLE devuser LOGIN PASSWORD 'devpass';
   END IF;
END
$$;

CREATE DATABASE devdb OWNER devuser;
GRANT ALL PRIVILEGES ON DATABASE devdb TO devuser;
SQL
EOF
RUN chmod +x /docker-entrypoint-initdb.d/init-user-db.sh

# Ensure Redis listens on all interfaces
RUN sed -ri "s/^bind .*/bind 0.0.0.0 ::/" /etc/redis/redis.conf && \
    sed -ri "s/^protected-mode yes/protected-mode no/" /etc/redis/redis.conf

# Configure Supervisor to run all services
RUN mkdir -p /var/log/supervisor

RUN cat > /etc/supervisor/conf.d/multi-service.conf << 'EOF'
[supervisord]
nodaemon=true
logfile=/var/log/supervisor/supervisord.log

[program:nginx]
command=/usr/sbin/nginx -g "daemon off;"
autostart=true
autorestart=true
stdout_logfile=/var/log/supervisor/nginx_stdout.log
stderr_logfile=/var/log/supervisor/nginx_stderr.log
priority=20

[program:api]
command=/opt/api/start-api.sh
directory=/opt/api
autostart=true
autorestart=true
stdout_logfile=/var/log/supervisor/api_stdout.log
stderr_logfile=/var/log/supervisor/api_stderr.log
priority=10

[program:postgresql]
command=/usr/lib/postgresql/14/bin/postgres -D /var/lib/postgresql/14/main -c config_file=/etc/postgresql/14/main/postgresql.conf
user=postgres
autostart=true
autorestart=true
stdout_logfile=/var/log/supervisor/postgres_stdout.log
stderr_logfile=/var/log/supervisor/postgres_stderr.log
priority=30

[program:redis]
command=/usr/bin/redis-server /etc/redis/redis.conf
autostart=true
autorestart=true
stdout_logfile=/var/log/supervisor/redis_stdout.log
stderr_logfile=/var/log/supervisor/redis_stderr.log
priority=40
EOF

# Initialize PostgreSQL data directory on build
RUN service postgresql start && \
    /docker-entrypoint-initdb.d/init-user-db.sh && \
    service postgresql stop

EXPOSE 80 8080 5432 6379

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/multi-service.conf"]