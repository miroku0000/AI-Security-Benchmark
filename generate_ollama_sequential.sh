#!/bin/bash
# Sequential Ollama code generation
# Runs one model at a time to avoid memory contention

set -e

echo "Starting sequential Ollama code generation..."
echo "Models will run one at a time"
echo ""

# List of Ollama models from benchmark_config.yaml
models=(
    "codellama"
    "deepseek-coder"
    "deepseek-coder:6.7b-instruct"
    "starcoder2"
    "codegemma"
    "mistral"
    "llama3.1"
    "qwen2.5-coder"
    "qwen2.5-coder:14b"
)

for model in "${models[@]}"; do
    # Convert model name to safe directory name (replace : with _)
    safe_name="${model//:/_}"

    echo "========================================"
    echo "Starting generation for: $model"
    echo "Output directory: output/$safe_name"
    echo "========================================"

    # Run code generation with 5-minute timeout per prompt (Ollama is slower)
    python3 code_generator.py \
        --model "$model" \
        --output "output/$safe_name" \
        --timeout 300 \
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
echo "All Ollama models completed!"
echo "========================================"
