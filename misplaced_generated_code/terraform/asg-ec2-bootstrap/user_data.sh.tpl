#!/bin/bash
set -euo pipefail
exec > >(tee /var/log/user-data.log|logger -t user-data -s 2>/dev/console) 2>&1

APP_PORT="${application_port}"
BACKEND_URL="${backend_api_url}"
REGION="${aws_region}"
TOKEN_PARAM="${backend_api_token_ssm_parameter}"

dnf install -y awscli jq

install -d -m 0755 /opt/app /etc/sysconfig

if [[ -n "$TOKEN_PARAM" ]]; then
  TOKEN=$(aws ssm get-parameter --region "$REGION" --name "$TOKEN_PARAM" --with-decryption --query 'Parameter.Value' --output text)
else
  TOKEN=""
fi

cat >/etc/sysconfig/app <<EOF
BACKEND_API_URL=$BACKEND_URL
BACKEND_API_TOKEN=$TOKEN
APP_PORT=$APP_PORT
EOF
chmod 0640 /etc/sysconfig/app

cat >/opt/app/server.py <<'PY'
import http.server
import os
import socketserver

port = int(os.environ.get("APP_PORT", "8080"))

class H(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")

with socketserver.TCPServer(("0.0.0.0", port), H) as httpd:
    httpd.serve_forever()
PY

cat >/etc/systemd/system/app.service <<EOF
[Unit]
Description=Demo app wired to backend env
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
EnvironmentFile=/etc/sysconfig/app
Environment=APP_PORT=$APP_PORT
ExecStart=/usr/bin/python3 /opt/app/server.py
Restart=always
RestartSec=2

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now app.service
