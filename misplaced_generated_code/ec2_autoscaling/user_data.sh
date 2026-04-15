#!/usr/bin/env bash
set -euo pipefail

exec > /var/log/user-data.log 2>&1
echo "$(date '+%Y-%m-%d %H:%M:%S') Starting instance bootstrap"

ENVIRONMENT="${environment}"
APP_NAME="${app_name}"
AWS_REGION="${aws_region}"
BACKEND_ENDPOINT="${backend_endpoint}"
BACKEND_PORT="${backend_port}"

yum update -y --security
yum install -y aws-cli jq amazon-cloudwatch-agent

echo "$(date '+%Y-%m-%d %H:%M:%S') Fetching configuration from SSM Parameter Store"
APP_CONFIG=$(aws ssm get-parameter \
  --name "/$ENVIRONMENT/$APP_NAME/config" \
  --with-decryption \
  --region "$AWS_REGION" \
  --query 'Parameter.Value' \
  --output text)

DB_HOST=$(echo "$APP_CONFIG" | jq -r '.db_host')
DB_NAME=$(echo "$APP_CONFIG" | jq -r '.db_name')
API_KEY_PARAM=$(echo "$APP_CONFIG" | jq -r '.api_key_ssm_param')

if [ -n "$API_KEY_PARAM" ]; then
  API_KEY=$(aws ssm get-parameter \
    --name "$API_KEY_PARAM" \
    --with-decryption \
    --region "$AWS_REGION" \
    --query 'Parameter.Value' \
    --output text)
fi

useradd --system --no-create-home --shell /usr/sbin/nologin appuser || true

mkdir -p /opt/$APP_NAME/config
chmod 750 /opt/$APP_NAME/config

cat > /opt/$APP_NAME/config/app.conf <<APPCONF
[backend]
endpoint = $BACKEND_ENDPOINT
port = $BACKEND_PORT

[database]
host = $DB_HOST
name = $DB_NAME
APPCONF

chmod 640 /opt/$APP_NAME/config/app.conf
chown -R appuser:appuser /opt/$APP_NAME

cat > /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json <<CWCONF
{
  "logs": {
    "logs_collected": {
      "files": {
        "collect_list": [
          {
            "file_path": "/var/log/$APP_NAME/*.log",
            "log_group_name": "/$ENVIRONMENT/$APP_NAME",
            "log_stream_name": "{instance_id}",
            "retention_in_days": 30
          }
        ]
      }
    }
  },
  "metrics": {
    "namespace": "$ENVIRONMENT/$APP_NAME",
    "metrics_collected": {
      "mem": { "measurement": ["mem_used_percent"] },
      "disk": { "measurement": ["used_percent"], "resources": ["*"] }
    }
  }
}
CWCONF

/opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
  -a fetch-config -m ec2 \
  -c file:/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json -s

echo "$(date '+%Y-%m-%d %H:%M:%S') Waiting for backend connectivity"
RETRIES=0
MAX_RETRIES=30
until curl -sf --max-time 5 "https://$BACKEND_ENDPOINT:$BACKEND_PORT/health" > /dev/null 2>&1; do
  RETRIES=$((RETRIES + 1))
  if [ "$RETRIES" -ge "$MAX_RETRIES" ]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') ERROR: Backend not reachable after $MAX_RETRIES attempts"
    exit 1
  fi
  echo "$(date '+%Y-%m-%d %H:%M:%S') Backend not ready, retry $RETRIES/$MAX_RETRIES"
  sleep 10
done

echo "$(date '+%Y-%m-%d %H:%M:%S') Backend reachable, starting application"

systemctl enable $APP_NAME
systemctl start $APP_NAME

echo "$(date '+%Y-%m-%d %H:%M:%S') Bootstrap complete"
