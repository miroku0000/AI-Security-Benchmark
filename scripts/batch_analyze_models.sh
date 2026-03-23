#!/bin/bash
# Batch analyze all base models (default temperature)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

# Models to process (base models without temperature suffix)
MODELS=(
    "chatgpt-4o-latest"
    "claude-code"
    "claude-opus-4-6"
    "claude-sonnet-4-5"
    "codegemma"
    "codellama"
    "codex-app"
    "cursor"
    "deepseek-coder"
    "deepseek-coder_6.7b-instruct"
    "gemini-2.5-flash"
    "gpt-3.5-turbo"
    "gpt-4"
    "gpt-4o"
    "gpt-4o-full-multilang"
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

echo "=========================================="
echo "AI Security Benchmark - Batch Analysis"
echo "Processing ${#MODELS[@]} base models"
echo "=========================================="
echo ""

# Create directories
mkdir -p reports
mkdir -p analysis/batch_results

# Counter
processed=0
failed=0
skipped=0

# Process each model
for model in "${MODELS[@]}"; do
    echo "[$((processed + failed + skipped + 1))/${#MODELS[@]}] $model"

    # Check if directory exists
    if [ ! -d "output/$model" ]; then
        echo "  ⊘ Directory not found, skipping"
        skipped=$((skipped + 1))
        continue
    fi

    # Count files
    file_count=$(find "output/$model" -type f \( -name "*.py" -o -name "*.js" -o -name "*.java" -o -name "*.cs" -o -name "*.cpp" -o -name "*.go" -o -name "*.rs" \) 2>/dev/null | wc -l | tr -d ' ')

    if [ "$file_count" = "0" ]; then
        echo "  ⊘ No code files found, skipping"
        skipped=$((skipped + 1))
        continue
    fi

    # Run benchmark
    report_file="reports/${model}_report.json"

    echo "  → Testing $file_count files..."

    if python3 runner.py \
        --code-dir "output/$model" \
        --model "$model" \
        --output "$report_file" \
        --no-html 2>&1 | tee "analysis/batch_results/${model}_test.log" | tail -15 | grep -E "Secure|Vulnerable|Score"; then

        processed=$((processed + 1))
        echo "  ✓ Complete"
    else
        failed=$((failed + 1))
        echo "  ✗ Failed"
    fi
    echo ""
done

echo "=========================================="
echo "Summary:"
echo "  Processed: $processed"
echo "  Failed: $failed"
echo "  Skipped: $skipped"
echo "=========================================="
