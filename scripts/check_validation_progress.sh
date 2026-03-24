#!/bin/bash
# Quick progress check for validation

echo "=== Level 4 Validation Progress ==="
echo ""

# Check if process is running
if ps -p 68363 > /dev/null 2>&1; then
    echo "Status: RUNNING (PID 68363)"
else
    echo "Status: COMPLETED or FAILED"
fi

echo ""
echo "Last 5 progress lines:"
grep -E "INFO.*\[[0-9]+/140\]" validation_output.log | tail -5 | sed 's/^INFO */  /'

echo ""
echo "Current progress:"
TOTAL=$(grep -E "INFO.*\[[0-9]+/140\]" validation_output.log | wc -l)
echo "  Files processed: $TOTAL/140 (~$(( TOTAL * 100 / 140 ))%)"

echo ""
echo "Errors (if any):"
grep -i "error\|failed" validation_output.log | tail -3 || echo "  None found"

echo ""
echo "To view full log: tail -f validation_output.log"
