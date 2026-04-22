#!/bin/bash

# Regenerate all base model reports with new detectors
# This script runs the benchmark runner for all 27 base models

echo "========================================="
echo "Regenerating All Base Model Reports"
echo "========================================="
echo ""

# Base models to regenerate (excluding temp/level variants)
models=(
    "claude-code"
    "claude-opus-4-6"
    "claude-sonnet-4-5"
    "codegemma"
    "codellama"
    "codex-app-no-skill"
    "codex-app-security-skill"
    "cursor"
    "deepseek-coder"
    "deepseek-coder_6.7b-instruct"
    "gemini-2.5-flash"
    "gpt-3.5-turbo"
    "gpt-4"
    "gpt-4o"
    "gpt-4o-mini"
    "gpt-5.2"
    "gpt-5.4"
    "gpt-5.4-mini"
    "llama3.1"
    "mistral"
    "o1"
    "o3"
    "o3-mini"
    "qwen2.5-coder"
    "qwen2.5-coder_14b"
    "qwen3-coder_30b"
    "starcoder2"
)

total=${#models[@]}
current=0

for model in "${models[@]}"; do
    current=$((current + 1))
    echo "[$current/$total] Processing $model..."

    # Check if output directory exists
    if [ ! -d "output/$model" ]; then
        echo "  ⚠️  Warning: output/$model not found, skipping..."
        continue
    fi

    # Run benchmark
    python3 runner.py --code-dir "output/$model" --model "$model" --output "reports/$model.json" --no-html

    if [ $? -eq 0 ]; then
        echo "  ✅ $model completed successfully"
    else
        echo "  ❌ $model failed"
    fi

    echo ""
done

echo "========================================="
echo "Regeneration Complete!"
echo "========================================="
echo ""
echo "Summary:"
echo "  Total models: $total"
echo "  Reports in: reports/"
echo ""
echo "Next steps:"
echo "  1. Check reports/ directory for new JSON files"
echo "  2. Run generate_summary_csv.py to update rankings"
echo "  3. Review updated scores"
