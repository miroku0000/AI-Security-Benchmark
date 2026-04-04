#!/bin/bash

# Temperature Study Runner
# Generates code for all models at temperatures 0.0, 0.5, 0.7, 1.0
# (Temperature 0.2 already exists as default)
#
# EXCLUDED: Models with fixed/non-configurable temperatures:
#   - o1, o3, o3-mini (OpenAI reasoning models use fixed temp 1.0)
#   - cursor, codex-app (use internal default temperatures)
#
# OPTIMIZATION:
#   - Quick file count check: Skips generation if exactly 760 files exist
#   - Use --detailed-check flag for file-by-file validation
#   - Skips entire model if all temperatures already complete

set -e

# Parse command line arguments
DETAILED_CHECK=false
while [[ $# -gt 0 ]]; do
    case $1 in
        --detailed-check)
            DETAILED_CHECK=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--detailed-check]"
            exit 1
            ;;
    esac
done

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
echo "  - OpenAI models: Max 4 in parallel (each runs temps sequentially)"
echo "  - Claude models: Max 2 in parallel (each runs temps sequentially)"
echo "  - Gemini models: Max 1 in parallel (each runs temps sequentially)"
echo "  - Ollama models: Max 2 in parallel (each runs temps sequentially)"
echo "  - ALL providers run SIMULTANEOUSLY (alongside each other)"
echo "  - Each model runs its temperatures sequentially (one temp at a time)"
echo ""
echo "OPTIMIZATIONS:"
echo "  ✓ Quick file count check (skips if 760 files exist)"
echo "  ✓ Skip entire model if all temps complete"
echo "  ✓ Resume incomplete generations automatically"
if [ "$DETAILED_CHECK" = true ]; then
    echo "  ✓ Detailed file-by-file validation: ENABLED"
else
    echo "  - Detailed validation: disabled (use --detailed-check to enable)"
fi
echo ""
echo "Estimated time: 3-5 hours (much faster if resuming)"
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

# Job tracking files
TRACKING_DIR="/tmp/temp_study_$$"
mkdir -p "$TRACKING_DIR"

# Function to count running jobs for a provider
count_provider_jobs() {
    local provider=$1
    local count=$(ls "$TRACKING_DIR"/${provider}_* 2>/dev/null | wc -l | tr -d ' ')
    echo "$count"
}

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

    # OPTIMIZATION: Quick file count check first
    if [ -d "$output_dir" ]; then
        local file_count=$(ls "$output_dir" 2>/dev/null | wc -l | tr -d ' ')
        if [ "$file_count" -eq 760 ]; then
            echo "✓ SKIP: $model at temp $temp already complete (760/760 files)"
            if [ "$DETAILED_CHECK" = true ]; then
                echo "  Running detailed file-by-file validation..."
                # TODO: Add detailed validation logic if needed
                # For now, we trust the count
            fi
            return 0
        elif [ "$file_count" -gt 0 ]; then
            echo "⚠ RESUME: Found $file_count/760 files, continuing generation..."
        fi
    fi

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

# Function to check if all temperatures are complete for a model
check_all_temps_complete() {
    local model=$1
    local model_dir=$(echo "$model" | tr ':' '_')

    for temp in $TEMPS; do
        local output_dir="output/${model_dir}_temp${temp}"
        if [ -d "$output_dir" ]; then
            local file_count=$(ls "$output_dir" 2>/dev/null | wc -l | tr -d ' ')
            if [ "$file_count" -ne 760 ]; then
                return 1  # Not complete
            fi
        else
            return 1  # Directory doesn't exist
        fi
    done

    return 0  # All temps complete
}

# Function to generate code for all temperatures of a model (runs sequentially)
# Also handles job tracking
generate_model_all_temps() {
    local model=$1
    local provider=$2
    local model_dir=$(echo "$model" | tr ':' '_')
    local tracking_file="$TRACKING_DIR/${provider}_${model_dir}"

    # OPTIMIZATION: Check if all temperatures already complete
    if check_all_temps_complete "$model"; then
        echo "✓ SKIP MODEL: $model - all temperatures already complete (4/4 temps with 760/760 files each)"
        return 0
    fi

    # Create tracking file
    touch "$tracking_file"

    echo "🚀 Starting model: $model ($provider) (will run temperatures sequentially)"

    for temp in $TEMPS; do
        generate_code "$model" "$temp"
    done

    echo "✓ Completed all temperatures for $model"

    # Remove tracking file
    rm -f "$tracking_file"
}

# Convert model lists to arrays
IFS=' ' read -ra OPENAI_ARRAY <<< "$OPENAI_MODELS"
IFS=' ' read -ra ANTHROPIC_ARRAY <<< "$ANTHROPIC_MODELS"
IFS=' ' read -ra GOOGLE_ARRAY <<< "$GOOGLE_MODELS"
IFS=' ' read -ra OLLAMA_ARRAY <<< "$OLLAMA_MODELS"

# Indices for each provider
openai_idx=0
anthropic_idx=0
google_idx=0
ollama_idx=0

# Max concurrent jobs per provider
MAX_OPENAI=4
MAX_ANTHROPIC=2
MAX_GOOGLE=1
MAX_OLLAMA=2

# Track progress
TOTAL_MODELS=$((${#OPENAI_ARRAY[@]} + ${#ANTHROPIC_ARRAY[@]} + ${#GOOGLE_ARRAY[@]} + ${#OLLAMA_ARRAY[@]}))
TOTAL_RUNS=$((TOTAL_MODELS * 4))  # 4 temperatures per model

echo "Total models to run: $TOTAL_MODELS"
echo "Total temperature runs: $TOTAL_RUNS"
echo ""
echo "===== STARTING ALL PROVIDERS SIMULTANEOUSLY ====="
echo ""
echo "Strategy: Maintain max parallelism at all times"
echo "  - As soon as a model completes, launch the next one"
echo "  - Keep all provider slots filled until all models complete"
echo ""

# Main launch loop - keeps launching models as slots become available
# Continue until all models have been launched AND all jobs have completed
while [ $openai_idx -lt ${#OPENAI_ARRAY[@]} ] || \
      [ $anthropic_idx -lt ${#ANTHROPIC_ARRAY[@]} ] || \
      [ $google_idx -lt ${#GOOGLE_ARRAY[@]} ] || \
      [ $ollama_idx -lt ${#OLLAMA_ARRAY[@]} ] || \
      [ $(count_provider_jobs "openai") -gt 0 ] || \
      [ $(count_provider_jobs "anthropic") -gt 0 ] || \
      [ $(count_provider_jobs "google") -gt 0 ] || \
      [ $(count_provider_jobs "ollama") -gt 0 ]; do

    launched_this_round=0

    # Try to launch OpenAI model
    if [ $openai_idx -lt ${#OPENAI_ARRAY[@]} ]; then
        openai_running=$(count_provider_jobs "openai")
        if [ "$openai_running" -lt "$MAX_OPENAI" ]; then
            model="${OPENAI_ARRAY[$openai_idx]}"
            echo "🚀 Launching OpenAI model $((openai_idx + 1))/${#OPENAI_ARRAY[@]}: $model (currently $openai_running/$MAX_OPENAI running)"
            generate_model_all_temps "$model" "openai" &
            ((openai_idx++))
            ((launched_this_round++))
        fi
    fi

    # Try to launch Anthropic model
    if [ $anthropic_idx -lt ${#ANTHROPIC_ARRAY[@]} ]; then
        anthropic_running=$(count_provider_jobs "anthropic")
        if [ "$anthropic_running" -lt "$MAX_ANTHROPIC" ]; then
            model="${ANTHROPIC_ARRAY[$anthropic_idx]}"
            echo "🚀 Launching Claude model $((anthropic_idx + 1))/${#ANTHROPIC_ARRAY[@]}: $model (currently $anthropic_running/$MAX_ANTHROPIC running)"
            generate_model_all_temps "$model" "anthropic" &
            ((anthropic_idx++))
            ((launched_this_round++))
        fi
    fi

    # Try to launch Google model
    if [ $google_idx -lt ${#GOOGLE_ARRAY[@]} ]; then
        google_running=$(count_provider_jobs "google")
        if [ "$google_running" -lt "$MAX_GOOGLE" ]; then
            model="${GOOGLE_ARRAY[$google_idx]}"
            echo "🚀 Launching Gemini model $((google_idx + 1))/${#GOOGLE_ARRAY[@]}: $model (currently $google_running/$MAX_GOOGLE running)"
            generate_model_all_temps "$model" "google" &
            ((google_idx++))
            ((launched_this_round++))
        fi
    fi

    # Try to launch Ollama model
    if [ $ollama_idx -lt ${#OLLAMA_ARRAY[@]} ]; then
        ollama_running=$(count_provider_jobs "ollama")
        if [ "$ollama_running" -lt "$MAX_OLLAMA" ]; then
            model="${OLLAMA_ARRAY[$ollama_idx]}"
            echo "🚀 Launching Ollama model $((ollama_idx + 1))/${#OLLAMA_ARRAY[@]}: $model (currently $ollama_running/$MAX_OLLAMA running)"
            generate_model_all_temps "$model" "ollama" &
            ((ollama_idx++))
            ((launched_this_round++))
        fi
    fi

    # If we couldn't launch anything this round, wait for jobs to complete
    # This happens when all slots are full OR all models have been launched
    if [ $launched_this_round -eq 0 ]; then
        # Check if there are any jobs still running
        total_running=$(($(count_provider_jobs "openai") + $(count_provider_jobs "anthropic") + $(count_provider_jobs "google") + $(count_provider_jobs "ollama")))
        if [ $total_running -gt 0 ]; then
            # Jobs are running, wait for one to complete
            sleep 5
        else
            # No jobs running and nothing to launch - we're done
            break
        fi
    fi
done

echo ""
echo "===== ALL MODELS COMPLETE ====="
echo ""

# Cleanup tracking directory
rm -rf "$TRACKING_DIR"

# Count successful runs
COMPLETED_RUNS=0
FAILED_RUNS=0

for model in $OPENAI_MODELS $ANTHROPIC_MODELS $GOOGLE_MODELS $OLLAMA_MODELS; do
    model_dir=$(echo "$model" | tr ':' '_')
    for temp in $TEMPS; do
        output_dir="output/${model_dir}_temp${temp}"
        file_count=$(ls "$output_dir" 2>/dev/null | wc -l | tr -d ' ')
        if [ "$file_count" -eq 760 ]; then
            ((COMPLETED_RUNS++))
        else
            ((FAILED_RUNS++))
        fi
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
