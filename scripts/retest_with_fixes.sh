#!/bin/bash
# Re-test all models with fixed detectors
# This script only re-runs security testing, NOT code generation
# Much faster than full regeneration

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

echo "==========================================="
echo "Re-testing All Models with Fixed Detectors"
echo "==========================================="
echo ""
echo "Fixes applied:"
echo "  1. Buffer overflow detector - word boundaries (fixed earlier)"
echo "  2. SQL injection detector - static query false positives (just fixed)"
echo ""
echo "This will re-run security tests on existing generated code."
echo "No code regeneration needed - detector fixes only."
echo ""

# Create backup of old reports
mkdir -p reports/pre-fix-backup
cp reports/*_208point_20260321.json reports/pre-fix-backup/ 2>/dev/null || true

echo "Backed up existing reports to reports/pre-fix-backup/"
echo ""

# Counter
processed=0
failed=0
skipped=0

# Find all model directories with code
for model_dir in output/*/; do
    model_name=$(basename "$model_dir")

    # Count files
    file_count=$(find "$model_dir" -type f \( -name "*.py" -o -name "*.js" -o -name "*.java" -o -name "*.cs" -o -name "*.cpp" -o -name "*.go" -o -name "*.rs" \) 2>/dev/null | wc -l | tr -d ' ')

    if [ "$file_count" = "0" ]; then
        echo "[$((processed + failed + skipped + 1))] $model_name - No code files, skipping"
        skipped=$((skipped + 1))
        continue
    fi

    echo "[$((processed + failed + skipped + 1))] $model_name ($file_count files)"

    # Run benchmark with fixed detectors
    report_file="reports/${model_name}_208point_20260321_fixed.json"

    if python3 runner.py \
        --code-dir "$model_dir" \
        --model "$model_name" \
        --output "$report_file" \
        --no-html 2>&1 | tail -20 | grep -E "Secure|Vulnerable|Score"; then

        processed=$((processed + 1))
        echo "  ✓ Complete - saved to $report_file"
    else
        failed=$((failed + 1))
        echo "  ✗ Failed"
    fi
    echo ""
done

echo "==========================================="
echo "Summary:"
echo "  Processed: $processed"
echo "  Failed: $failed"
echo "  Skipped: $skipped"
echo "==========================================="
echo ""
echo "Compare results:"
echo "  Before: reports/pre-fix-backup/*_208point_20260321.json"
echo "  After:  reports/*_208point_20260321_fixed.json"
echo ""
