#!/bin/bash

# Single Model Temperature Study Runner
# Test temperature study on a single model before running the full batch
#
# Usage: ./scripts/run_single_model_temperature_study.sh <model_name>
# Example: ./scripts/run_single_model_temperature_study.sh deepseek-coder

set -e

if [ $# -eq 0 ]; then
    echo "Usage: $0 <model_name>"
    echo ""
    echo "Available models:"
    echo "  OpenAI: gpt-3.5-turbo, gpt-4, gpt-4o, gpt-4o-mini, gpt-5.2, gpt-5.4, gpt-5.4-mini"
    echo "  Anthropic: claude-opus-4-6, claude-sonnet-4-5"
    echo "  Google: gemini-2.5-flash"
    echo "  Ollama: codellama, deepseek-coder, deepseek-coder:6.7b-instruct, starcoder2, codegemma, mistral, llama3.1, qwen2.5-coder, qwen2.5-coder:14b"
    echo ""
    echo "Example: $0 deepseek-coder"
    exit 1
fi

MODEL=$1

echo "========================================="
echo "Single Model Temperature Study"
echo "========================================="
echo ""
echo "Model: $MODEL"
echo "Temperatures: 0.0, 0.5, 0.7, 1.0"
echo "Prompts: 760"
echo "Total files: 3,040"
echo ""
echo "Estimated time: 30-90 minutes depending on model"
echo ""
echo "Starting..."
echo ""

# Temperature settings
TEMPS="0.0 0.5 0.7 1.0"

# Track progress
COMPLETED=0
FAILED=0

# Generate code for each temperature
for temp in $TEMPS; do
    echo ""
    echo "========================================="
    echo "Temperature: $temp"
    echo "========================================="

    # Sanitize model name for directory (replace : with _)
    model_dir=$(echo "$MODEL" | tr ':' '_')
    output_dir="output/${model_dir}_temp${temp}"

    python3 code_generator.py --model "$MODEL" --temperature "$temp" --output "$output_dir" --force-regenerate --retries 3

    if [ $? -eq 0 ]; then
        # Verify all 760 files were generated
        file_count=$(ls "$output_dir" 2>/dev/null | wc -l | tr -d ' ')
        if [ "$file_count" -eq 760 ]; then
            echo "✓ Successfully generated code at temperature $temp (760/760 files)"
            ((COMPLETED++))
        else
            echo "⚠ Generated code at temperature $temp but only $file_count/760 files created"
            echo "  Retrying to complete missing files..."
            python3 code_generator.py --model "$MODEL" --temperature "$temp" --output "$output_dir" --retries 3
            file_count=$(ls "$output_dir" 2>/dev/null | wc -l | tr -d ' ')
            if [ "$file_count" -eq 760 ]; then
                echo "✓ Completed missing files: $file_count/760 files"
                ((COMPLETED++))
            else
                echo "✗ Still incomplete: $file_count/760 files"
                ((FAILED++))
            fi
        fi
    else
        echo "✗ Failed to generate code at temperature $temp"
        ((FAILED++))
    fi

    echo "Progress: $COMPLETED completed, $FAILED failed"
done

# Run security analysis for each temperature
echo ""
echo "========================================="
echo "Running Security Analysis"
echo "========================================="

for temp in $TEMPS; do
    model_dir=$(echo "$MODEL" | tr ':' '_')
    output_dir="output/${model_dir}_temp${temp}"
    model_name="${model_dir}_temp${temp}"

    echo ""
    echo "Analyzing: $model_name"

    python3 runner.py --code-dir "$output_dir" --model "$model_name"

    if [ $? -eq 0 ]; then
        echo "✓ Analysis complete for temperature $temp"
    else
        echo "✗ Analysis failed for temperature $temp"
    fi
done

# Final summary
echo ""
echo "========================================="
echo "SINGLE MODEL TEMPERATURE STUDY COMPLETE"
echo "========================================="
echo "Model: $MODEL"
echo "Temperatures completed: $COMPLETED/4"
echo "Temperatures failed: $FAILED/4"
echo ""
echo "Next steps:"
echo "  1. View results: python3 generate_temperature_table_760_prompts.py"
echo "  2. Compare with baseline: cat reports/${model_dir}_report.json"
echo "  3. If successful, run full study: bash scripts/run_temperature_study.sh"
echo ""
