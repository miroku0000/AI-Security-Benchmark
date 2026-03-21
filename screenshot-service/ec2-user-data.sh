#!/bin/bash
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y docker.io
systemctl enable docker
systemctl start docker
usermod -aG docker ubuntu || true
