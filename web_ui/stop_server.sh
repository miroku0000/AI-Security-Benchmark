#!/bin/bash

# SAST UI Server Stop Script
# Gracefully stops the Flask server

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}🛑 Stopping SAST UI Server...${NC}"

# Kill any Python processes running the Flask app
PIDS=$(pgrep -f "python.*app.py" 2>/dev/null || true)

if [ -z "$PIDS" ]; then
    echo -e "${YELLOW}ℹ️  No Flask server processes found${NC}"
else
    echo -e "${YELLOW}🔍 Found Flask server processes: $PIDS${NC}"

    # First try graceful shutdown
    kill $PIDS 2>/dev/null || true

    # Wait a moment for graceful shutdown
    sleep 2

    # Force kill if still running
    REMAINING=$(pgrep -f "python.*app.py" 2>/dev/null || true)
    if [ ! -z "$REMAINING" ]; then
        echo -e "${YELLOW}⚠️  Force killing remaining processes...${NC}"
        kill -9 $REMAINING 2>/dev/null || true
    fi
fi

# Also clean up anything using port 5000
LSOF_OUTPUT=$(lsof -ti:5000 2>/dev/null || true)
if [ ! -z "$LSOF_OUTPUT" ]; then
    echo -e "${YELLOW}🧹 Cleaning up port 5000...${NC}"
    lsof -ti:5000 | xargs kill -9 2>/dev/null || true
fi

echo -e "${GREEN}✅ SAST UI Server stopped${NC}"