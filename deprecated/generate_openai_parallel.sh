#!/bin/bash
# Parallel OpenAI code generation
# Runs all models simultaneously

set -e

echo "Starting PARALLEL OpenAI code generation..."
echo "All models will run simultaneously"
echo ""

# List of OpenAI models from benchmark_config.yaml
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

# Array to track PIDs
pids=()

# Launch all models in parallel
for model in "${models[@]}"; do
    # Convert model name to safe directory name
    safe_name="${model//:/_}"

    echo "Launching: $model -> output/$safe_name (logs to ${safe_name}.log)"

    # Run in background
    python3 code_generator.py \
        --model "$model" \
        --output "output/$safe_name" \
        --timeout 120 \
        --retries 2 \
        > "${safe_name}.log" 2>&1 &

    # Store PID
    pids+=($!)
done

echo ""
echo "========================================"
echo "Launched ${#models[@]} parallel processes"
echo "PIDs: ${pids[@]}"
echo "========================================"
echo ""
echo "Monitor progress with:"
echo "  tail -f gpt-*.log o1.log o3*.log"
echo ""
echo "Waiting for all to complete..."

# Wait for all background processes
failed=0
for i in "${!pids[@]}"; do
    pid=${pids[$i]}
    model=${models[$i]}

    if wait $pid; then
        echo "✓ Completed: $model"
    else
        echo "✗ Failed: $model"
        ((failed++))
    fi
done

echo ""
echo "========================================"
echo "All OpenAI models completed!"
echo "Success: $((${#models[@]} - failed))/${#models[@]}"
echo "Failed: $failed/${#models[@]}"
echo "========================================"
