#!/bin/bash

echo "========================================="
echo "Regenerating ALL Baseline Models"
echo "140 prompts, 346-point scale"
echo "========================================="
echo ""

# All baseline models (24 total)
MODELS=(
    "gpt-3.5-turbo"
    "gpt-4"
    "gpt-4o"
    "gpt-4o-mini"
    "gpt-5.2"
    "gpt-5.4"
    "gpt-5.4-mini"
    "o1"
    "o3"
    "o3-mini"
    "claude-opus-4-6"
    "claude-sonnet-4-5"
    "gemini-2.5-flash"
    "codellama"
    "deepseek-coder"
    "deepseek-coder:6.7b-instruct"
    "starcoder2"
    "codegemma"
    "mistral"
    "llama3.1"
    "qwen2.5-coder"
    "qwen2.5-coder:14b"
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
        echo "✗ Failed: $model"
    fi
    echo ""
done

echo "========================================="
echo "Baseline Regeneration Complete"
echo "========================================="
echo "Total models: $TOTAL"
echo "Completed: $COMPLETED"
