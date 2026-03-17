#!/bin/bash
# retest_priority2.sh - Test Priority 2 OpenAI standard models

MODELS=(
    "gpt-4"
    "gpt-4o"
    "gpt-4o-mini"
    "gpt-3.5-turbo"
    "o1"
)

for model in "${MODELS[@]}"; do
    echo "========================================="
    echo "Testing: $model"
    echo "========================================="

    python3 runner.py \
        --code-dir "generated_${model}" \
        --model "${model}" \
        --output "reports/${model}_208point_$(date +%Y%m%d_%H%M%S).json"

    echo "Completed: $model"
    echo ""
done

echo "========================================="
echo "Phase 3 Complete: All Priority 2 models tested"
echo "========================================="
