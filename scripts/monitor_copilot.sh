#!/bin/bash
# Continuous monitor for GitHub Copilot generation progress

while true; do
    clear
    echo "GitHub Copilot Generation Monitor"
    echo "=================================="
    echo "$(date)"
    echo ""
    
    # Run status.py and extract just the GitHub Copilot line
    python3 status.py 2>/dev/null | grep -A 0 "GitHub Copilot CLI"
    
    echo ""
    echo "Files in output/github-copilot/:"
    file_count=$(ls -1 output/github-copilot/*.py output/github-copilot/*.js output/github-copilot/*.java output/github-copilot/*.go 2>/dev/null | wc -l | tr -d ' ')
    echo "$file_count / 730 generated"
    
    echo ""
    echo "Press Ctrl+C to stop monitoring"
    
    sleep 5
done
