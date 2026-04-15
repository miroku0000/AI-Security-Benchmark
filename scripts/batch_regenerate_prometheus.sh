#!/bin/bash
# Batch regenerate prometheus code for all baseline models

set -e

MODELS=(
    "claude-code"
    "claude-opus-4-6"
    "claude-sonnet-4-5"
    "codegemma"
    "codellama"
    "codex-app-no-skill"
    "codex-app-security-skill"
    "codex"
    "cursor"
    "deepseek-coder_6.7b-instruct"
    "deepseek-coder"
    "gemini-2.5-flash"
    "gpt-3.5-turbo"
    "gpt-4"
    "gpt-4o-mini"
    "gpt-4o"
    "gpt-5.2"
    "gpt-5.4-mini"
    "gpt-5.4"
    "llama3.1"
    "mistral"
    "o1"
    "o3-mini"
    "o3"
    "qwen2.5-coder_14b"
    "qwen2.5-coder"
    "starcoder2"
)

echo "================================================================================"
echo "BATCH PROMETHEUS REGENERATION - BASELINE MODELS"
echo "================================================================================"
echo "Models to process: ${#MODELS[@]}"
echo "Prometheus prompt: prompts/prompts_prometheus_fixed.yaml"
echo "Using FAIR baseline (no adversarial prompt)"
echo "================================================================================"
echo ""

SUCCESS_COUNT=0
FAIL_COUNT=0

for MODEL in "${MODELS[@]}"; do
    echo "[$((SUCCESS_COUNT + FAIL_COUNT + 1))/${#MODELS[@]}] Processing: $MODEL"
    echo "--------------------------------------------------------------------------------"

    # Generate code
    if python3 code_generator.py --model "$MODEL" --prompts prompts/prompts_prometheus_fixed.yaml --force-regenerate --no-cache 2>&1 | grep -q "Newly generated:\s*1"; then
        # Move from generated/ to output/MODEL/
        if [ -f "generated/obs_prometheus_001.py" ]; then
            mkdir -p "output/$MODEL"
            mv "generated/obs_prometheus_001.py" "output/$MODEL/obs_prometheus_001.py"
            echo "✅ Success: $MODEL"
            SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
        else
            echo "❌ Failed: File not generated for $MODEL"
            FAIL_COUNT=$((FAIL_COUNT + 1))
        fi
    else
        echo "❌ Failed: Generation failed for $MODEL"
        FAIL_COUNT=$((FAIL_COUNT + 1))
    fi

    echo ""
done

echo "================================================================================"
echo "BATCH REGENERATION SUMMARY"
echo "================================================================================"
echo "✅ Successful: $SUCCESS_COUNT"
echo "❌ Failed: $FAIL_COUNT"
echo "================================================================================"
