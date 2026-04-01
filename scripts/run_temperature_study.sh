#!/bin/bash

# Temperature Study Runner
# Generates code for all models at temperatures 0.0, 0.5, 0.7, 1.0
# (Temperature 0.2 already exists as default)
#
# EXCLUDED: Models with fixed/non-configurable temperatures:
#   - o1, o3, o3-mini (OpenAI reasoning models use fixed temp 1.0)
#   - cursor, codex-app (use internal default temperatures)

set -e

echo "========================================="
echo "AI Security Benchmark - Temperature Study"
echo "========================================="
echo ""
echo "This will generate code for:"
echo "  - 19 models (excludes o1/o3/cursor/codex - fixed temps)"
echo "  - 4 temperature settings (0.0, 0.5, 0.7, 1.0)"
echo "  - 760 prompts each"
echo "  = 57,760 total code files"
echo ""
echo "Parallelization strategy:"
echo "  - OpenAI models: Fully parallel (7 models × 4 temps = 28 concurrent)"
echo "  - Anthropic models: Max 2 parallel (2 models × 4 temps = 8 with max 2)"
echo "  - Google models: Max 2 parallel (1 model × 4 temps = 4 with max 2)"
echo "  - Ollama models: Max 2 parallel (9 models × 4 temps = 36 with max 2)"
echo ""
echo "Estimated time: 3-5 hours (was 8-12 hours sequential)"
echo ""
echo "Starting temperature study..."
echo ""

# List of models for temperature study
# NOTE: o1, o3, o3-mini, cursor, codex-app excluded (fixed temperatures)
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
    local log_file="logs/${model_dir}_temp${temp}.log"

    # Create logs directory if it doesn't exist
    mkdir -p logs

    # Run without --force-regenerate to allow resuming interrupted runs
    # Files that already exist will be skipped automatically
    python3 code_generator.py --model "$model" --temperature "$temp" --output "$output_dir" --retries 3 > "$log_file" 2>&1

    if [ $? -eq 0 ]; then
        # Verify all 760 files were generated
        local file_count=$(ls "$output_dir" 2>/dev/null | wc -l | tr -d ' ')
        if [ "$file_count" -eq 760 ]; then
            echo "✓ Successfully generated code for $model at temperature $temp (760/760 files)"
        else
            echo "⚠ Generated code for $model at temperature $temp but only $file_count/760 files created"
            echo "  Retrying to complete missing files..."
            # Retry without force-regenerate to complete missing files
            python3 code_generator.py --model "$model" --temperature "$temp" --output "$output_dir" --retries 3 >> "$log_file" 2>&1
            file_count=$(ls "$output_dir" 2>/dev/null | wc -l | tr -d ' ')
            if [ "$file_count" -eq 760 ]; then
                echo "✓ Completed missing files: $file_count/760 files"
            else
                echo "✗ Still incomplete: $file_count/760 files"
                return 1
            fi
        fi
    else
        echo "✗ Failed to generate code for $model at temperature $temp"
        return 1
    fi
}

# Function to wait for background jobs to finish with max concurrency limit
wait_for_slot() {
    local max_jobs=$1
    while [ $(jobs -r | wc -l) -ge "$max_jobs" ]; do
        sleep 5
    done
}

# Function to generate code in background
generate_code_bg() {
    local model=$1
    local temp=$2
    local model_dir=$(echo "$model" | tr ':' '_')
    local output_dir="output/${model_dir}_temp${temp}"
    local log_file="logs/${model_dir}_temp${temp}.log"

    mkdir -p logs

    echo "🚀 Starting background: $model temp=$temp"

    # Run in background with nohup
    nohup python3 code_generator.py --model "$model" --temperature "$temp" --output "$output_dir" --retries 3 > "$log_file" 2>&1 &

    # Store the PID
    echo $! > "/tmp/tempgen_${model_dir}_${temp}.pid"
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

# Generate code for OpenAI models (fully parallel - high rate limits)
echo "===== OPENAI MODELS (FULLY PARALLEL) ====="
echo "Starting all OpenAI models in background (high rate limits)..."

for model in $OPENAI_MODELS; do
    for temp in $TEMPS; do
        generate_code_bg "$model" "$temp"
        ((COMPLETED_RUNS++))
    done
done

echo "✓ Started ${#OPENAI_MODELS[@]} OpenAI models × 4 temperatures"
echo ""

# Generate code for Anthropic models with concurrency limit of 2
# Claude API has rate limits, so run max 2 at a time
echo "===== ANTHROPIC MODELS (MAX 2 PARALLEL) ====="
echo "Starting Anthropic models with max 2 concurrent (API rate limits)..."

for model in $ANTHROPIC_MODELS; do
    for temp in $TEMPS; do
        wait_for_slot 2
        generate_code_bg "$model" "$temp"
        ((COMPLETED_RUNS++))
    done
done

echo "✓ Started ${#ANTHROPIC_MODELS[@]} Anthropic models × 4 temperatures"
echo ""

# Generate code for Google models with concurrency limit of 2
# Google has strict rate limits
echo "===== GOOGLE MODELS (MAX 2 PARALLEL) ====="
echo "Starting Google models with max 2 concurrent (strict rate limits)..."

for model in $GOOGLE_MODELS; do
    for temp in $TEMPS; do
        wait_for_slot 2
        generate_code_bg "$model" "$temp"
        ((COMPLETED_RUNS++))
    done
done

echo "✓ Started ${#GOOGLE_MODELS[@]} Google models × 4 temperatures"
echo ""

# Generate code for Ollama models with concurrency limit of 2
# Ollama uses local GPU/CPU, so limit to 2 parallel to avoid memory issues
echo "===== OLLAMA MODELS (MAX 2 PARALLEL) ====="
echo "Starting Ollama models with max 2 concurrent (local GPU/memory)..."

for model in $OLLAMA_MODELS; do
    for temp in $TEMPS; do
        wait_for_slot 2
        generate_code_bg "$model" "$temp"
        ((COMPLETED_RUNS++))
    done
done

echo "✓ Started ${#OLLAMA_MODELS[@]} Ollama models × 4 temperatures"
echo ""
echo "===== ALL MODELS STARTED ====="
echo "Total processes launched: $COMPLETED_RUNS/$TOTAL_RUNS"
echo ""
echo "⏳ Waiting for all background processes to complete..."
echo "   Monitor progress: python3 status.sh"
echo ""

# Wait for all background jobs to complete
wait

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
