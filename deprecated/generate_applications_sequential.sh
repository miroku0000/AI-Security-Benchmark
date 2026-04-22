#!/bin/bash
# Sequential application-based code generation
# Runs Cursor, Codex.app, and Claude Code CLI one at a time
# Now uses code_generator.py which automatically delegates to test scripts

set -e

echo "Starting sequential application-based code generation..."
echo "Models will run one at a time"
echo ""

# List of application models from benchmark_config.yaml
# code_generator.py now automatically detects these and delegates to:
# - cursor -> scripts/test_cursor.py
# - codex-app -> scripts/test_codex_app.py
# - claude-code -> built-in claude-cli provider
models=(
    "cursor"
    "codex-app"
    "claude-code"
)

for model in "${models[@]}"; do
    # Convert model name to safe directory name (replace : with _)
    safe_name="${model//:/_}"

    echo "========================================"
    echo "Starting generation for: $model"
    echo "Output directory: output/$safe_name"
    echo "========================================"

    # Run code generation with appropriate timeout
    # code_generator.py will automatically delegate to the proper script
    python3 code_generator.py \
        --model "$model" \
        --output "output/$safe_name" \
        --timeout 180 \
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
echo "All application models completed!"
echo "========================================"
