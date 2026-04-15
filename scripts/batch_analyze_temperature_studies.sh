#!/bin/bash
# Batch analyze all temperature study variants

set -e

echo "================================================================================"
echo "BATCH TEMPERATURE STUDY ANALYSIS"
echo "================================================================================"

# Find all temperature directories
TEMP_DIRS=($(ls -1d output/*_temp* 2>/dev/null | sort))

echo "Temperature variants to process: ${#TEMP_DIRS[@]}"
echo "Output: reports/[model]_analysis.json"
echo "================================================================================"
echo ""

SUCCESS_COUNT=0
FAIL_COUNT=0
START_TIME=$(date +%s)

for CODE_DIR in "${TEMP_DIRS[@]}"; do
    # Extract model name from directory (e.g., "output/claude-opus-4-6_temp0.5" -> "claude-opus-4-6_temp0.5")
    MODEL=$(basename "$CODE_DIR")
    OUTPUT_FILE="reports/${MODEL}_analysis.json"

    echo "[$((SUCCESS_COUNT + FAIL_COUNT + 1))/${#TEMP_DIRS[@]}] Processing: $MODEL"
    echo "--------------------------------------------------------------------------------"

    # Check if output directory exists and has files
    if [ ! -d "$CODE_DIR" ]; then
        echo "❌ Failed: Directory not found: $CODE_DIR"
        FAIL_COUNT=$((FAIL_COUNT + 1))
        echo ""
        continue
    fi

    FILE_COUNT=$(ls -1 "$CODE_DIR" 2>/dev/null | wc -l)
    if [ "$FILE_COUNT" -eq 0 ]; then
        echo "⚠️  Warning: No files in $CODE_DIR, skipping"
        FAIL_COUNT=$((FAIL_COUNT + 1))
        echo ""
        continue
    fi

    echo "   Files to analyze: $FILE_COUNT"

    # Extract temperature from model name for the --temperature flag
    TEMP=$(echo "$MODEL" | grep -oE 'temp[0-9.]+' | sed 's/temp//')

    # Run analysis with temperature auto-detection
    if python3 runner.py --code-dir "$CODE_DIR" --output "$OUTPUT_FILE" --model "$MODEL" --temperature "$TEMP" 2>&1 | tail -5; then
        echo "✅ Success: $MODEL ($OUTPUT_FILE)"
        SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
    else
        echo "❌ Failed: Analysis failed for $MODEL"
        FAIL_COUNT=$((FAIL_COUNT + 1))
    fi

    echo ""
done

END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))
MINUTES=$((ELAPSED / 60))
SECONDS=$((ELAPSED % 60))

echo "================================================================================"
echo "BATCH TEMPERATURE ANALYSIS SUMMARY"
echo "================================================================================"
echo "✅ Successful: $SUCCESS_COUNT"
echo "❌ Failed: $FAIL_COUNT"
echo "⏱️  Time elapsed: ${MINUTES}m ${SECONDS}s"
echo "================================================================================"
