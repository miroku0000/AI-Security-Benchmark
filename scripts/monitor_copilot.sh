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
    file_count=$(ls -1 output/github-copilot/ 2>/dev/null | grep -v 'generation_results' | wc -l | tr -d ' ')
    echo "$file_count / 730 generated"
    
    echo ""
    echo "Press Ctrl+C to stop monitoring"
    
    sleep 5
done
