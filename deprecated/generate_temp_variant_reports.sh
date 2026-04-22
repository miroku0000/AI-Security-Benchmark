#!/bin/bash

echo "========================================="
echo "Generating Temperature Variant Reports"
echo "========================================="
echo ""

# Find all temperature variant output directories
TEMP_DIRS=$(ls -d output/*_temp* 2>/dev/null)

TOTAL=$(echo "$TEMP_DIRS" | wc -l | tr -d ' ')
COMPLETED=0
FAILED=0

echo "Found $TOTAL temperature variant directories"
echo ""

for output_dir in $TEMP_DIRS; do
    # Extract model name from directory (e.g., output/claude-opus-4-6_temp0.0 -> claude-opus-4-6_temp0.0)
    model_name=$(basename "$output_dir")

    # Check if report already exists
    report_file="reports/${model_name}_analysis.json"

    if [ -f "$report_file" ]; then
        echo "[SKIP] $model_name (report already exists)"
        ((COMPLETED++))
        continue
    fi

    # Check if output directory has files
    file_count=$(ls "$output_dir" 2>/dev/null | wc -l | tr -d ' ')
    if [ "$file_count" -eq 0 ]; then
        echo "[SKIP] $model_name (no output files)"
        continue
    fi

    echo "[$((COMPLETED + FAILED + 1))/$TOTAL] Generating report for $model_name..."

    # Run validation
    python3 runner.py \
        --code-dir "$output_dir" \
        --output "$report_file" \
        --model "$model_name" \
        --no-html \
        2>&1 | tee "logs/${model_name}_validation.log"

    if [ $? -eq 0 ]; then
        ((COMPLETED++))
        echo "  ✓ Complete: $report_file"
    else
        ((FAILED++))
        echo "  ✗ Failed"
    fi
    echo ""
done

echo ""
echo "========================================="
echo "Temperature Variant Reports Complete"
echo "========================================="
echo "Total:     $TOTAL"
echo "Generated: $COMPLETED"
echo "Failed:    $FAILED"
echo "Skipped:   $((TOTAL - COMPLETED - FAILED))"
echo ""
