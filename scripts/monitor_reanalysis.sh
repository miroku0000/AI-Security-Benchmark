#!/bin/bash
#
# Monitor re-analysis progress
#

LOG_FILE="logs/full_reanalysis_20260323.log"

echo "Monitoring re-analysis progress..."
echo ""

while true; do
    clear
    echo "======================================================================"
    echo "Re-Analysis Progress Monitor"
    echo "======================================================================"
    echo "Time: $(date)"
    echo ""

    # Count completed
    completed=$(grep -c "✓ Success:" "$LOG_FILE" 2>/dev/null || echo "0")
    failed=$(grep -c "✗ Failed:" "$LOG_FILE" 2>/dev/null || echo "0")

    # Current model
    current=$(tail -5 "$LOG_FILE" 2>/dev/null | grep "Analyzing:" | tail -1 | sed 's/Analyzing: //')

    echo "Completed: $completed"
    echo "Failed: $failed"
    echo "Total processed: $((completed + failed))"
    echo ""
    echo "Currently analyzing: ${current:-waiting...}"
    echo ""
    echo "======================================================================"
    echo "Recent detections:"
    echo "----------------------------------------------------------------------"
    tail -20 "$LOG_FILE" 2>/dev/null | grep -E "(VULNERABLE|SECURE|✓|✗)" | tail -15
    echo "======================================================================"
    echo ""
    echo "Press Ctrl+C to exit"

    sleep 10
done
