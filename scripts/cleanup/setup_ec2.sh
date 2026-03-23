#!/bin/bash

# Update system
sudo apt-get update
sudo apt-get upgrade -y

# Install Python and pip
sudo apt-get install -y python3 python3-pip python3-venv

# Install Chrome
wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
sudo sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list'
sudo apt-get update
sudo apt-get install -y google-chrome-stable

# Install ChromeDriver
CHROME_VERSION=$(google-chrome --version | awk '{print $3}' | cut -d'.' -f1)
wget -q https://chromedriver.storage.googleapis.com/LATEST_RELEASE_${CHROME_VERSION} -O /tmp/chromedriver_version
CHROMEDRIVER_VERSION=$(cat /tmp/chromedriver_version)
wget -q https://chromedriver.storage.googleapis.com/${CHROMEDRIVER_VERSION}/chromedriver_linux64.zip -O /tmp/chromedriver.zip
sudo apt-get install -y unzip
sudo unzip -o /tmp/chromedriver.zip -d /usr/bin/
sudo chmod +x /usr/bin/chromedriver

# Install additional dependencies
sudo apt-get install -y libglib2.0-0 libnss3 libgconf-2-4 libfontconfig1

# Create app directory
mkdir -p /home/ubuntu/screenshot-service
cd /home/ubuntu/screenshot-service

# Copy application files (assuming they're uploaded)
# cp screenshot_service.py .
# cp requirements_screenshot.txt .

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install --upgrade pip
pip install -r requirements_screenshot.txt

# Create systemd service
sudo tee /etc/systemd/system/screenshot-service.service > /dev/null <<EOF
[Unit]
Description=Screenshot Service
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/screenshot-service
Environment="PATH=/home/ubuntu/screenshot-service/venv/bin"
Environment="AWS_ACCESS_KEY_ID=YOUR_AWS_ACCESS_KEY"
Environment="AWS_SECRET_ACCESS_KEY=YOUR_AWS_SECRET_KEY"
Environment="S3_BUCKET_NAME=screenshot-thumbnails"
Environment="AWS_DEFAULT_REGION=us-east-1"
Environment="CHROMEDRIVER_PATH=/usr/bin/chromedriver"
ExecStart=/home/ubuntu/screenshot-service/venv/bin/gunicorn -w 4 -b 0.0.0.0:5000 screenshot_service:app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable screenshot-service
sudo systemctl start screenshot-service

# Setup nginx (optional)
sudo apt-get install -y nginx
sudo tee /etc/nginx/sites-available/screenshot-service > /dev/null <<EOF
server {
    listen 80;
    server_name _;
    
    client_max_body_size 10M;
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
EOF

sudo ln -s /etc/nginx/sites-available/screenshot-service /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx

echo "Setup complete! Remember to:"
echo "1. Update AWS credentials in /etc/systemd/system/screenshot-service.service"
echo "2. Copy your application files to /home/ubuntu/screenshot-service/"
echo "3. Restart the service: sudo systemctl restart screenshot-service"
echo "4. Check logs: sudo journalctl -u screenshot-service -f"