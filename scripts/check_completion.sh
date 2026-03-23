#!/bin/bash
while true; do
    GEMINI_PID=$(ps aux | grep 42362 | grep -v grep)
    if [ -z "$GEMINI_PID" ]; then
        echo "Gemini retry completed at $(date '+%I:%M %p')"
        echo "Final counts:"
        for temp in 0.0 0.5 0.7 1.0; do
            count=$(ls output/gemini-2.5-flash_temp$temp/ 2>/dev/null | wc -l | tr -d ' ')
            echo "  gemini temp $temp: $count/141"
        done
        exit 0
    fi
    sleep 60
done
