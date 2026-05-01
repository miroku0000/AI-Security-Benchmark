#!/bin/bash

# SAST UI Server Startup Script
# Handles virtual environment setup and ensures Python 3 is used

set -e

# Script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Starting SAST UI Server...${NC}"

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 is required but not found${NC}"
    exit 1
fi

echo -e "${YELLOW}📍 Working directory: $SCRIPT_DIR${NC}"
echo -e "${YELLOW}🐍 Python version: $(python3 --version)${NC}"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}📦 Creating virtual environment...${NC}"
    python3 -m venv venv
fi

# Activate virtual environment
echo -e "${YELLOW}🔌 Activating virtual environment...${NC}"
source venv/bin/activate

# Upgrade pip
echo -e "${YELLOW}⬆️  Upgrading pip...${NC}"
python -m pip install --upgrade pip

# Install requirements if they exist
if [ -f "requirements.txt" ]; then
    echo -e "${YELLOW}📋 Installing dependencies from requirements.txt...${NC}"
    pip install -r requirements.txt
else
    echo -e "${YELLOW}📋 Installing basic Flask dependencies...${NC}"
    pip install flask flask-cors requests
fi

# Kill any existing processes on port 5000
echo -e "${YELLOW}🧹 Cleaning up any existing processes on port 5000...${NC}"
lsof -ti:5000 | xargs kill -9 2>/dev/null || true

# Wait a moment for cleanup
sleep 2

# Set environment variables
export FLASK_APP=app.py
export FLASK_ENV=production
export PYTHONPATH="$SCRIPT_DIR:$PYTHONPATH"

# Start the server
echo -e "${GREEN}🌟 Starting Flask server on http://localhost:5000${NC}"
echo -e "${YELLOW}📝 Logs will appear below. Press Ctrl+C to stop.${NC}"
echo ""

python app.py