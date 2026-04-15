#!/bin/bash
# Regenerate all code with 730 fair prompts for all baseline models

MODELS=(
    "codex-app-security-skill"
    "claude-opus-4-6"
    "claude-sonnet-4-5"
    "gpt-4o"
    "gpt-5.4"
    "deepseek-coder"
    "o1"
    "gemini-2.5-flash"
    "qwen2.5-coder"
    "codellama"
    "starcoder2"
    "deepseek-coder_6.7b-instruct"
    "codegemma"
    "mistral"
    "codex-app-no-skill"
    "llama3.1"
    "qwen2.5-coder_14b"
    "gpt-5.4-mini"
    "gpt-4o-mini"
    "gpt-3.5-turbo"
    "gpt-5.2"
    "gpt-4"
    "o3-mini"
    "claude-code"
    "o3"
    "codex"
    "cursor"
)

echo "================================================================================"
echo "FULL REGENERATION WITH FAIR PROMPTS ONLY"
echo "================================================================================"
echo "Total models: ${#MODELS[@]}"
echo "Total prompts: 730 (27 adversarial prompts removed)"
echo "Estimated time: ~2-3 hours for all models"
echo "================================================================================"
echo ""

for MODEL in "${MODELS[@]}"; do
    echo ""
    echo "================================================================================"
    echo "GENERATING: $MODEL"
    echo "================================================================================"
    
    python3 auto_benchmark.py --model "$MODEL" 2>&1 | tee "logs/regeneration_${MODEL}.log"
    
    echo "✅ Completed: $MODEL"
done

echo ""
echo "================================================================================"
echo "REGENERATION COMPLETE"
echo "================================================================================"
