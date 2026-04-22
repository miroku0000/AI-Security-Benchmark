#!/bin/bash

echo "========================================="
echo "Generating Missing Analysis Reports"
echo "========================================="

MODELS=(
    "claude-code"
    "claude-opus-4-6"
    "codegemma"
    "codellama"
    "codex-app-no-skill"
    "deepseek-coder_6.7b-instruct"
    "gemini-2.5-flash"
    "gpt-3.5-turbo"
    "gpt-4"
    "gpt-4o-mini"
    "gpt-5.2"
    "gpt-5.4-mini"
    "llama3.1"
    "mistral"
    "o1"
    "o3"
    "o3-mini"
    "qwen2.5-coder"
    "qwen2.5-coder_14b"
    "starcoder2"
)

TOTAL=${#MODELS[@]}
COMPLETED=0
FAILED=0

for model in "${MODELS[@]}"; do
    echo ""
    echo "[$((COMPLETED + FAILED + 1))/$TOTAL] Analyzing $model..."
    
    python3 runner.py \
        --code-dir "output/$model" \
        --output "reports/${model}_analysis.json" \
        --model "$model" \
        --no-html \
        2>&1 | tail -20
    
    if [ $? -eq 0 ]; then
        ((COMPLETED++))
        echo "  ✓ Complete: reports/${model}_analysis.json"
    else
        ((FAILED++))
        echo "  ✗ Failed"
    fi
done

echo ""
echo "========================================="
echo "Summary:"
echo "  Completed: $COMPLETED"
echo "  Failed: $FAILED"
echo "  Total: $TOTAL"
echo "========================================="
