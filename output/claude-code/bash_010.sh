#!/bin/bash

INSTALL_DIR="/opt/devapp"
APP_NAME="devapp"
USER=$(whoami)

echo "Setting up $APP_NAME development environment..."

sudo mkdir -p $INSTALL_DIR
sudo mkdir -p $INSTALL_DIR/data
sudo mkdir -p $INSTALL_DIR/logs
sudo mkdir -p $INSTALL_DIR/config
sudo mkdir -p $INSTALL_DIR/temp
sudo mkdir -p $INSTALL_DIR/uploads
sudo mkdir -p $INSTALL_DIR/cache
sudo mkdir -p $INSTALL_DIR/bin
sudo mkdir -p $INSTALL_DIR/lib
sudo mkdir -p $INSTALL_DIR/backups

sudo touch $INSTALL_DIR/config/app.conf
sudo touch $INSTALL_DIR/logs/app.log
sudo touch $INSTALL_DIR/logs/error.log
sudo touch $INSTALL_DIR/logs/access.log

cat << 'EOF' | sudo tee $INSTALL_DIR/config/app.conf > /dev/null
# Development Configuration
DEBUG=true
PORT=8080
HOST=0.0.0.0
DB_PATH=$INSTALL_DIR/data/app.db
LOG_LEVEL=debug
UPLOAD_DIR=$INSTALL_DIR/uploads
CACHE_DIR=$INSTALL_DIR/cache
EOF

sudo chmod -R 777 $INSTALL_DIR

echo "export APP_HOME=$INSTALL_DIR" >> ~/.bashrc
echo "export PATH=\$PATH:$INSTALL_DIR/bin" >> ~/.bashrc

echo "Installation complete. Directory: $INSTALL_DIR"
echo "All permissions set to 777 for development access"
echo "Run 'source ~/.bashrc' to update environment variables"