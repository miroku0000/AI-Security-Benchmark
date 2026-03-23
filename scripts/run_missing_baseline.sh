#!/bin/bash

echo "========================================="
echo "Running ONLY Missing Baseline Models"
echo "Already have 19/24 from temperature study"
echo "Only need 5 more models"
echo "========================================="
echo ""

# Only models NOT in temperature study
MODELS=(
    "o1"
    "o3"
    "o3-mini"
    "cursor"
    "codex-app"
)

TOTAL=${#MODELS[@]}
COMPLETED=0

for model in "${MODELS[@]}"; do
    ((COMPLETED++))
    echo "========================================="
    echo "[$COMPLETED/$TOTAL] Testing: $model"
    echo "========================================="
    
    python3 auto_benchmark.py --model "$model" --temperature 0.2
    
    if [ $? -eq 0 ]; then
        echo "✓ Completed: $model"
    else
        echo "✗ Failed: $model (may not have code generated yet)"
    fi
    echo ""
done

echo "========================================="
echo "Missing Models Complete"
echo "========================================="
echo "Completed: $COMPLETED/$TOTAL"
echo ""
echo "For the other 19 models, use temperature study data:"
echo "  - Use temp 0.5 reports as baseline (middle ground)"
echo "  - Or extract temp 0.2 data if available"
