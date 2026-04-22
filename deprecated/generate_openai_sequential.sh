#!/bin/bash
# Sequential OpenAI code generation
# Runs one model at a time

set -e

echo "Starting sequential OpenAI code generation..."
echo "Models will run one at a time"
echo ""

# List of OpenAI models from benchmark_config.yaml
# gpt-5.4 is already running, so start with the remaining ones
models=(
    "gpt-3.5-turbo"
    "gpt-4"
    "gpt-4o"
    "gpt-4o-mini"
    "o1"
    "o3"
    "o3-mini"
    "gpt-5.2"
    "gpt-5.4-mini"
)

for model in "${models[@]}"; do
    # Convert model name to safe directory name (replace : with _)
    safe_name="${model//:/_}"

    echo "========================================"
    echo "Starting generation for: $model"
    echo "Output directory: output/$safe_name"
    echo "========================================"

    # Run code generation with 120s timeout per prompt
    python3 code_generator.py \
        --model "$model" \
        --output "output/$safe_name" \
        --timeout 120 \
        --retries 2

    exit_code=$?

    if [ $exit_code -eq 0 ]; then
        echo "✓ Successfully completed: $model"
    else
        echo "✗ Failed with exit code $exit_code: $model"
        echo "Continuing with next model..."
    fi

    echo ""
done

echo "========================================"
echo "All OpenAI models completed!"
echo "========================================"
