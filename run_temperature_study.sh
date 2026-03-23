#!/bin/bash

# Temperature Study Runner
# Generates code for all models at temperatures 0.0, 0.5, 0.7, 1.0
# (Temperature 0.2 already exists as default)

set -e

echo "========================================="
echo "AI Security Benchmark - Temperature Study"
echo "========================================="
echo ""
echo "This will generate code for:"
echo "  - 19 models"
echo "  - 4 temperature settings (0.0, 0.5, 0.7, 1.0)"
echo "  - 141 prompts each"
echo "  = 10,716 total code files"
echo ""
echo "Estimated time: 8-12 hours"
echo ""
echo "Starting temperature study..."
echo ""

# List of models for temperature study
OPENAI_MODELS="gpt-3.5-turbo gpt-4 gpt-4o gpt-4o-mini gpt-5.2 gpt-5.4 gpt-5.4-mini"
ANTHROPIC_MODELS="claude-opus-4-6 claude-sonnet-4-5"
GOOGLE_MODELS="gemini-2.5-flash"
OLLAMA_MODELS="codellama deepseek-coder deepseek-coder:6.7b-instruct starcoder2 codegemma mistral llama3.1 qwen2.5-coder qwen2.5-coder:14b"

# Temperature settings
TEMPS="0.0 0.5 0.7 1.0"

# Function to generate code for a model at a specific temperature
generate_code() {
    local model=$1
    local temp=$2

    echo ""
    echo "========================================="
    echo "Model: $model"
    echo "Temperature: $temp"
    echo "========================================="

    # Sanitize model name for directory (replace : with _)
    local model_dir=$(echo "$model" | tr ':' '_')
    local output_dir="output/${model_dir}_temp${temp}"

    python3 code_generator.py --model "$model" --temperature "$temp" --output "$output_dir" --force-regenerate --retries 3

    if [ $? -eq 0 ]; then
        # Verify all 141 files were generated
        local file_count=$(ls "$output_dir" 2>/dev/null | wc -l | tr -d ' ')
        if [ "$file_count" -eq 141 ]; then
            echo "✓ Successfully generated code for $model at temperature $temp (141/141 files)"
        else
            echo "⚠ Generated code for $model at temperature $temp but only $file_count/141 files created"
            echo "  Retrying to complete missing files..."
            # Retry without force-regenerate to complete missing files
            python3 code_generator.py --model "$model" --temperature "$temp" --output "$output_dir" --retries 3
            file_count=$(ls "$output_dir" 2>/dev/null | wc -l | tr -d ' ')
            if [ "$file_count" -eq 141 ]; then
                echo "✓ Completed missing files: $file_count/141 files"
            else
                echo "✗ Still incomplete: $file_count/141 files"
                return 1
            fi
        fi
    else
        echo "✗ Failed to generate code for $model at temperature $temp"
        return 1
    fi
}

# Track progress
TOTAL_RUNS=0
COMPLETED_RUNS=0
FAILED_RUNS=0

# Calculate total runs
for model in $OPENAI_MODELS $ANTHROPIC_MODELS $GOOGLE_MODELS $OLLAMA_MODELS; do
    for temp in $TEMPS; do
        ((TOTAL_RUNS++))
    done
done

echo "Total runs to complete: $TOTAL_RUNS"
echo ""

# Generate code for OpenAI models
echo "===== OPENAI MODELS ====="
for model in $OPENAI_MODELS; do
    for temp in $TEMPS; do
        if generate_code "$model" "$temp"; then
            ((COMPLETED_RUNS++))
        else
            ((FAILED_RUNS++))
        fi
        echo "Progress: $COMPLETED_RUNS/$TOTAL_RUNS completed, $FAILED_RUNS failed"
    done
done

# Generate code for Anthropic models
echo ""
echo "===== ANTHROPIC MODELS ====="
for model in $ANTHROPIC_MODELS; do
    for temp in $TEMPS; do
        if generate_code "$model" "$temp"; then
            ((COMPLETED_RUNS++))
        else
            ((FAILED_RUNS++))
        fi
        echo "Progress: $COMPLETED_RUNS/$TOTAL_RUNS completed, $FAILED_RUNS failed"
    done
done

# Generate code for Google models
echo ""
echo "===== GOOGLE MODELS ====="
for model in $GOOGLE_MODELS; do
    for temp in $TEMPS; do
        if generate_code "$model" "$temp"; then
            ((COMPLETED_RUNS++))
        else
            ((FAILED_RUNS++))
        fi
        echo "Progress: $COMPLETED_RUNS/$TOTAL_RUNS completed, $FAILED_RUNS failed"
    done
done

# Generate code for Ollama models (run sequentially to avoid memory issues)
echo ""
echo "===== OLLAMA MODELS ====="
for model in $OLLAMA_MODELS; do
    for temp in $TEMPS; do
        if generate_code "$model" "$temp"; then
            ((COMPLETED_RUNS++))
        else
            ((FAILED_RUNS++))
        fi
        echo "Progress: $COMPLETED_RUNS/$TOTAL_RUNS completed, $FAILED_RUNS failed"
    done
done

# Final summary
echo ""
echo "========================================="
echo "TEMPERATURE STUDY COMPLETE"
echo "========================================="
echo "Total runs: $TOTAL_RUNS"
echo "Completed: $COMPLETED_RUNS"
echo "Failed: $FAILED_RUNS"
echo ""
echo "Next steps:"
echo "  1. Run security analysis: python3 runner.py --model <model_name> --temperature <temp>"
echo "  2. Generate reports: python3 analyze_temperature_results.py"
echo ""
