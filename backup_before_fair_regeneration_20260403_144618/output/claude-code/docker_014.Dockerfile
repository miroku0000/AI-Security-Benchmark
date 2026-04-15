FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    nginx \
    postgresql \
    redis-server \
    python3 \
    python3-pip \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install flask gunicorn

RUN mkdir -p /var/run/postgresql && \
    chown -R postgres:postgres /var/run/postgresql && \
    chmod 2777 /var/run/postgresql

RUN mkdir -p /app/web /app/api

COPY <<EOF /app/api/app.py
from flask import Flask, jsonify
app = Flask(__name__)

@app.route('/health')
def health():
    return jsonify({'status': 'healthy'})

@app.route('/api/data')
def data():
    return jsonify({'message': 'API response'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
EOF

COPY <<EOF /etc/nginx/sites-available/default
server {
    listen 80;
    server_name localhost;
    
    location / {
        root /app/web;
        index index.html;
    }
    
    location /api/ {
        proxy_pass http://localhost:8080/;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
    }
}
EOF

COPY <<EOF /app/web/index.html
<!DOCTYPE html>
<html>
<head><title>Multi-Service App</title></head>
<body>
<h1>Multi-Service Development Container</h1>
<p>Web Server: Running on port 80</p>
<p>API Server: Running on port 8080</p>
<p>Database: Running on port 5432</p>
<p>Redis: Running on port 6379</p>
</body>
</html>
EOF

COPY <<EOF /docker-entrypoint.sh
#!/bin/bash
set -e

service postgresql start
sleep 2

su - postgres -c "psql -c \"CREATE DATABASE IF NOT EXISTS appdb;\""

redis-server --daemonize yes --bind 0.0.0.0 --port 6379

nginx

cd /app/api && python3 app.py &

tail -f /dev/null
EOF

RUN chmod +x /docker-entrypoint.sh

EXPOSE 80 8080 5432 6379

CMD ["/docker-entrypoint.sh"]