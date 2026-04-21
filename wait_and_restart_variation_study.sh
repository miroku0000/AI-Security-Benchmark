#!/bin/bash
# Wait for current claude-opus-4-6 generation to complete, then restart parallel study

echo "=========================================="
echo "VARIATION STUDY - WAIT AND RESTART"
echo "=========================================="
echo ""

TARGET_DIR="variation_study/claude-opus-4-6_temp0.5/run2"
TARGET_FILES=730

echo "Waiting for claude-opus-4-6 to complete..."
echo "Target: $TARGET_FILES files in $TARGET_DIR"
echo ""

# Monitor until complete
while true; do
    if [ -d "$TARGET_DIR" ]; then
        file_count=$(ls "$TARGET_DIR" | grep -v generation.log | wc -l | tr -d ' ')

        if [ "$file_count" -ge "$TARGET_FILES" ]; then
            echo ""
            echo "✓ Claude-opus-4-6 complete! ($file_count files)"
            echo ""
            break
        else
            echo "⏳ Progress: $file_count/$TARGET_FILES files ($(date '+%H:%M:%S'))"
        fi
    else
        echo "⚠ Directory not found: $TARGET_DIR"
    fi

    sleep 120  # Check every 2 minutes
done

# Wait a bit for process cleanup
echo "Waiting 30 seconds for process cleanup..."
sleep 30

# Check if any code_generator processes are still running
echo ""
echo "Checking for active processes..."
active=$(ps aux | grep code_generator.py | grep -v grep | wc -l | tr -d ' ')

if [ "$active" -gt 0 ]; then
    echo "⚠ Warning: $active code_generator process(es) still running"
    echo "Waiting for them to finish..."
    while [ "$active" -gt 0 ]; do
        sleep 30
        active=$(ps aux | grep code_generator.py | grep -v grep | wc -l | tr -d ' ')
    done
fi

echo "✓ All processes complete"
echo ""

# Restart the parallel study
echo "=========================================="
echo "RESTARTING PARALLEL VARIATION STUDY"
echo "=========================================="
echo ""
echo "Starting at: $(date)"
echo ""

nohup python3 run_variation_study_parallel.py > variation_study_restart_$(date +%Y%m%d_%H%M%S).log 2>&1 &

RESTART_PID=$!
echo "✓ Parallel study restarted with PID: $RESTART_PID"
echo ""
echo "Monitor progress with:"
echo "  tail -f variation_study_restart_*.log"
echo "  python3 monitor_variation_study.py"
echo ""
echo "=========================================="
