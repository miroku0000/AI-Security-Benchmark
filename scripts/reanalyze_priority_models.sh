#!/bin/bash
# Re-analyze priority models with improved detectors

MODELS=(
    "claude-opus-4-6"
    "claude-sonnet-4-5"
    "gpt-4o"
    "gpt-5.2"
    "gpt-5.4"
    "deepseek-coder"
    "qwen2.5-coder"
    "codex-app-security-skill"
    "o3-mini"
)

mkdir -p reports/improved_detectors

for model in "${MODELS[@]}"; do
    echo "========================================="
    echo "Analyzing: $model"
    echo "========================================="

    python3 runner.py \
        --code-dir "output/$model" \
        --output "reports/improved_detectors/${model}_analysis.json" \
        --model "$model" \
        --temperature 0.0 \
        2>&1 | tee "reports/improved_detectors/${model}_run.log"

    echo ""
    echo "Completed: $model"
    echo ""
done

echo "All analyses complete!"
