#!/bin/bash
# retest_priority3.sh - Test Priority 3 Ollama open-source models

MODELS=(
    "deepseek-coder"
    "deepseek-coder:6.7b-instruct"
    "codellama"
    "codegemma"
    "codegemma:7b-instruct"
    "qwen2.5-coder"
    "mistral"
)

echo "========================================="
echo "Testing Ollama models in parallel"
echo "========================================="

# These are Ollama models - can run in parallel
for model in "${MODELS[@]}"; do
    echo "Starting: $model"
    python3 runner.py \
        --code-dir "generated_${model}" \
        --model "${model}" \
        --output "reports/${model}_208point_$(date +%Y%m%d_%H%M%S).json" &
done

wait  # Wait for all parallel jobs

echo "========================================="
echo "Phase 4 Complete: All Priority 3 models tested"
echo "========================================="
