#!/bin/bash

# Regenerate all temperature and level variant reports with new detectors
# This script runs the benchmark runner for all temperature/level variants

echo "========================================="
echo "Regenerating Temperature/Level Variants"
echo "========================================="
echo ""

# Get all temperature and level variant directories
variants=($(ls -d output/*temp* output/*level* 2>/dev/null | sed 's|output/||' | sort))

total=${#variants[@]}
current=0
success_count=0
fail_count=0

echo "Found $total temperature/level variants to regenerate"
echo ""

for variant in "${variants[@]}"; do
    current=$((current + 1))
    echo "[$current/$total] Processing $variant..."

    # Check if output directory exists
    if [ ! -d "output/$variant" ]; then
        echo "  ⚠️  Warning: output/$variant not found, skipping..."
        fail_count=$((fail_count + 1))
        continue
    fi

    # Extract temperature or level from variant name for metadata
    temp_or_level=""
    if [[ $variant == *"_temp"* ]]; then
        temp_or_level=$(echo "$variant" | grep -o 'temp[0-9.]*' | sed 's/temp//')
        temp_flag="--temperature $temp_or_level"
    else
        temp_flag=""
    fi

    # Run benchmark
    python3 runner.py \
        --code-dir "output/$variant" \
        --model "$variant" \
        --output "reports/$variant.json" \
        --no-html \
        $temp_flag

    if [ $? -eq 0 ]; then
        echo "  ✅ $variant completed successfully"
        success_count=$((success_count + 1))
    else
        echo "  ❌ $variant failed"
        fail_count=$((fail_count + 1))
    fi

    echo ""
done

echo "========================================="
echo "Regeneration Complete!"
echo "========================================="
echo ""
echo "Summary:"
echo "  Total variants: $total"
echo "  Successful: $success_count"
echo "  Failed: $fail_count"
echo "  Reports in: reports/"
echo ""
echo "Next steps:"
echo "  1. Check reports/ directory for new JSON files"
echo "  2. Verify temperature/level variants are correct"
echo "  3. Update temperature study analysis"
