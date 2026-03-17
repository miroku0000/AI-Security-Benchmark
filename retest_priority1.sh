#!/bin/bash
# retest_priority1.sh - Test Priority 1 high-performing models

MODELS=(
    "starcoder2:7b"
    "starcoder2"
    "qwen2.5-coder:14b"
    "o3"
    "o3-mini"
    "gpt-5.2"
)

for model in "${MODELS[@]}"; do
    echo "========================================="
    echo "Testing: $model"
    echo "========================================="

    # Run benchmark with existing code
    python3 runner.py \
        --code-dir "generated_${model}" \
        --model "${model}" \
        --output "reports/${model}_208point_$(date +%Y%m%d_%H%M%S).json"

    echo "Completed: $model"
    echo ""
done

echo "========================================="
echo "Phase 2 Complete: All Priority 1 models tested"
echo "========================================="
