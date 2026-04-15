#!/bin/bash
# Batch regenerate baseline model analysis reports (exclude temp and level studies)

set -e

MODELS=(
    "claude-code"
    "claude-opus-4-6"
    "claude-sonnet-4-5"
    "codegemma"
    "codellama"
    "codex"
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
    "starcoder2"
)

echo "================================================================================"
echo "BATCH BASELINE REPORT REGENERATION"
echo "================================================================================"
echo "Models to process: ${#MODELS[@]}"
echo "Output: reports/[model]_analysis.json"
echo "================================================================================"
echo ""

SUCCESS_COUNT=0
FAIL_COUNT=0
START_TIME=$(date +%s)

for MODEL in "${MODELS[@]}"; do
    echo "[$((SUCCESS_COUNT + FAIL_COUNT + 1))/${#MODELS[@]}] Processing: $MODEL"
    echo "--------------------------------------------------------------------------------"

    CODE_DIR="output/$MODEL"
    OUTPUT_FILE="reports/${MODEL}_analysis.json"

    # Check if output directory exists and has files
    if [ ! -d "$CODE_DIR" ]; then
        echo "❌ Failed: Directory not found: $CODE_DIR"
        FAIL_COUNT=$((FAIL_COUNT + 1))
        echo ""
        continue
    fi

    FILE_COUNT=$(ls -1 "$CODE_DIR" 2>/dev/null | wc -l)
    if [ "$FILE_COUNT" -eq 0 ]; then
        echo "⚠️  Warning: No files in $CODE_DIR, skipping"
        FAIL_COUNT=$((FAIL_COUNT + 1))
        echo ""
        continue
    fi

    echo "   Files to analyze: $FILE_COUNT"

    # Run analysis
    if python3 runner.py --code-dir "$CODE_DIR" --output "$OUTPUT_FILE" --model "$MODEL" 2>&1 | tail -5; then
        echo "✅ Success: $MODEL ($OUTPUT_FILE)"
        SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
    else
        echo "❌ Failed: Analysis failed for $MODEL"
        FAIL_COUNT=$((FAIL_COUNT + 1))
    fi

    echo ""
done

END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))
MINUTES=$((ELAPSED / 60))
SECONDS=$((ELAPSED % 60))

echo "================================================================================"
echo "BATCH REGENERATION SUMMARY"
echo "================================================================================"
echo "✅ Successful: $SUCCESS_COUNT"
echo "❌ Failed: $FAIL_COUNT"
echo "⏱️  Time elapsed: ${MINUTES}m ${SECONDS}s"
echo "================================================================================"
