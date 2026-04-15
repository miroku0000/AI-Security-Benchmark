#!/bin/bash
# Sequential Claude (Anthropic) code generation
# Runs one model at a time

set -e

echo "Starting sequential Claude code generation..."
echo "Models will run one at a time"
echo ""

# List of Claude models from benchmark_config.yaml
# claude-opus-4-6 is already running, so start with the next one
models=(
    "claude-sonnet-4-5"
)

for model in "${models[@]}"; do
    # Convert model name to safe directory name (replace : with _)
    safe_name="${model//:/_}"

    echo "========================================"
    echo "Starting generation for: $model"
    echo "Output directory: output/$safe_name"
    echo "========================================"

    # Run code generation with 120s timeout per prompt
    # Use CLAUDE_CODE_USE_BEDROCK=0 to force direct API (not Bedrock)
    CLAUDE_CODE_USE_BEDROCK=0 python3 code_generator.py \
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
echo "All Claude models completed!"
echo "========================================"
