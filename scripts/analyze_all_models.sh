#!/bin/bash
# Script to analyze all models for false positives/negatives

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

# Create analysis directory
mkdir -p analysis/model_reports

echo "=========================================="
echo "AI Security Benchmark - Batch Model Analysis"
echo "=========================================="
echo ""

# Counter
total_models=0
processed_models=0
failed_models=0

# Find all model directories with code
for model_dir in output/*/; do
    model_name=$(basename "$model_dir")

    # Count files
    file_count=$(find "$model_dir" -type f \( -name "*.py" -o -name "*.js" -o -name "*.java" -o -name "*.cs" -o -name "*.cpp" -o -name "*.go" -o -name "*.rs" \) 2>/dev/null | wc -l | tr -d ' ')

    if [ "$file_count" -gt 0 ]; then
        total_models=$((total_models + 1))
        echo "[$total_models] Processing: $model_name ($file_count files)"

        # Run benchmark
        report_file="reports/${model_name}_report.json"

        if python3 runner.py \
            --code-dir "$model_dir" \
            --model "$model_name" \
            --output "$report_file" \
            --no-html 2>&1 | tee "analysis/model_reports/${model_name}_test.log" | grep -E "SUMMARY|Score|Secure|Vulnerable"; then

            processed_models=$((processed_models + 1))
            echo "  ✓ Report saved: $report_file"
        else
            failed_models=$((failed_models + 1))
            echo "  ✗ Failed to process $model_name"
        fi
        echo ""
    fi
done

echo "=========================================="
echo "Summary:"
echo "  Total models with code: $total_models"
echo "  Successfully processed: $processed_models"
echo "  Failed: $failed_models"
echo "=========================================="
