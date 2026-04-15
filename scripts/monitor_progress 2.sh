#!/bin/bash
LOG_FILE="temperature_study_20260321_193151.log"

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║     AI Security Benchmark - Temperature Study Monitor         ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

PID=$(pgrep -f run_temperature_study)
if [ -n "$PID" ]; then
    echo "✓ Status: RUNNING (PID: $PID)"
else
    echo "✗ Status: STOPPED"
fi

echo "📅 Started: $(ls -l $LOG_FILE 2>/dev/null | awk '{print $6, $7, $8}')"
echo ""
echo "📊 Current Activity:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
tail -10 $LOG_FILE 2>/dev/null | grep -E "(Model:|Temperature:|\\[.*\\])" | tail -5 || echo "Starting..."
echo ""

COMPLETIONS=$(grep -c "Successfully generated code" $LOG_FILE 2>/dev/null)
echo "✅ Completed runs: $COMPLETIONS/76"
echo "📁 Total directories: $(ls -d output/*_temp* 2>/dev/null | wc -l | tr -d ' ')"

if [ $COMPLETIONS -gt 0 ]; then
    echo ""
    echo "🎯 Recent Completions:"
    grep "Successfully generated code" $LOG_FILE 2>/dev/null | tail -3
fi

echo ""
echo "To monitor: watch -n 10 ./monitor_progress.sh"
