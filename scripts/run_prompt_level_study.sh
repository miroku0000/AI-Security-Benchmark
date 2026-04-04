#!/usr/bin/env bash
# Multi-Level Security Prompt Study Runner
# Runs levels 1-5 for specified models (Level 0 already exists as baseline)
# Supports parallel execution: 2 Claude + 4 OpenAI + 2 Ollama models concurrently

# Use bash 4+ for associative arrays
if [ "${BASH_VERSINFO[0]}" -lt 4 ]; then
    echo "ERROR: This script requires bash 4 or higher (you have bash ${BASH_VERSION})"
    echo "On macOS, install bash 5: brew install bash"
    echo "Then run with: /usr/local/bin/bash $0 $@"
    exit 1
fi

set -e

# Function to determine model type
get_model_type() {
    local model=$1
    if [[ "$model" == *"claude"* ]]; then
        echo "claude"
    elif [[ "$model" == *"gpt"* ]]; then
        echo "openai"
    else
        echo "ollama"
    fi
}

# Function to run single model study
run_model_study() {
    local MODEL=$1
    local MODEL_TYPE=$2

    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting study for $MODEL ($MODEL_TYPE)"

    # Check if Level 0 (baseline) exists
    if [ ! -d "output/$MODEL" ]; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] WARNING: Level 0 (baseline) not found for $MODEL"
    fi

    # Run levels 1-5
    for level in 1 2 3 4 5; do
        OUTPUT_DIR="output/${MODEL}_level${level}"
        PROMPT_FILE="prompts/prompts_level${level}_security.yaml"

        if [ ! -f "$PROMPT_FILE" ]; then
            echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: Prompt file not found: $PROMPT_FILE"
            continue
        fi

        echo "[$(date '+%Y-%m-%d %H:%M:%S')] $MODEL: Running Level $level"

        # Generate code
        python3 code_generator.py \
            --model "$MODEL" \
            --prompts "$PROMPT_FILE" \
            --output "$OUTPUT_DIR" \
            --retries 2 \
            --timeout 180 \
            2>&1 | tee "logs/${MODEL}_level${level}_generation.log"

        # Run security analysis
        python3 runner.py \
            --code-dir "$OUTPUT_DIR" \
            --model "${MODEL}_level${level}" \
            2>&1 | tee "logs/${MODEL}_level${level}_analysis.log"

        echo "[$(date '+%Y-%m-%d %H:%M:%S')] $MODEL: Level $level complete"
    done

    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Study complete for $MODEL"
}

# Parse arguments
PARALLEL=false
MODELS=()

while [[ $# -gt 0 ]]; do
    case $1 in
        --parallel)
            PARALLEL=true
            shift
            ;;
        *)
            MODELS+=("$1")
            shift
            ;;
    esac
done

# Handle single model (backward compatibility)
if [ ${#MODELS[@]} -eq 0 ]; then
    echo "Usage: $0 [--parallel] <model_name> [model_name2 ...]"
    echo ""
    echo "Single model example: $0 gpt-4o-mini"
    echo "Parallel example:     $0 --parallel gpt-4o-mini claude-sonnet-4.5 deepseek-coder"
    echo ""
    echo "Available models:"
    echo "  API Models: gpt-4o-mini, gpt-4o, claude-opus-4.6, claude-sonnet-4.5"
    echo "  Ollama Models: deepseek-coder, qwen2.5-coder, codellama, llama3.1"
    echo ""
    echo "Parallel limits:"
    echo "  - Claude models: 2 concurrent"
    echo "  - OpenAI models: 4 concurrent"
    echo "  - Ollama models: 2 concurrent"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

# Create logs directory if not exists
mkdir -p logs

echo "========================================"
echo "Multi-Level Security Prompt Study"
echo "========================================"
echo "Models: ${MODELS[@]}"
echo "Levels: 1-5"
echo "Parallel: $PARALLEL"
echo "========================================"
echo ""

# Non-parallel execution (backward compatible)
if [ "$PARALLEL" = false ]; then
    for MODEL in "${MODELS[@]}"; do
        MODEL_TYPE=$(get_model_type "$MODEL")
        run_model_study "$MODEL" "$MODEL_TYPE"
    done
    exit 0
fi

# Parallel execution with limits
declare -A running_models
claude_count=0
openai_count=0
ollama_count=0

# Max concurrent per type
MAX_CLAUDE=2
MAX_OPENAI=4
MAX_OLLAMA=2

for MODEL in "${MODELS[@]}"; do
    MODEL_TYPE=$(get_model_type "$MODEL")

    # Wait if we've hit the limit for this type
    while true; do
        # Count running processes by type
        claude_count=0
        openai_count=0
        ollama_count=0

        for pid in "${!running_models[@]}"; do
            if kill -0 "$pid" 2>/dev/null; then
                type="${running_models[$pid]}"
                case $type in
                    claude) ((claude_count++)) ;;
                    openai) ((openai_count++)) ;;
                    ollama) ((ollama_count++)) ;;
                esac
            else
                # Process finished, remove it
                unset running_models[$pid]
            fi
        done

        # Check if we can start this model type
        can_start=false
        case $MODEL_TYPE in
            claude)
                if [ $claude_count -lt $MAX_CLAUDE ]; then
                    can_start=true
                fi
                ;;
            openai)
                if [ $openai_count -lt $MAX_OPENAI ]; then
                    can_start=true
                fi
                ;;
            ollama)
                if [ $ollama_count -lt $MAX_OLLAMA ]; then
                    can_start=true
                fi
                ;;
        esac

        if [ "$can_start" = true ]; then
            break
        fi

        # Wait before checking again
        sleep 5
    done

    # Start the model study in background
    run_model_study "$MODEL" "$MODEL_TYPE" &
    pid=$!
    running_models[$pid]="$MODEL_TYPE"

    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Started $MODEL (PID: $pid, Type: $MODEL_TYPE)"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Currently running: Claude=$claude_count/$MAX_CLAUDE, OpenAI=$openai_count/$MAX_OPENAI, Ollama=$ollama_count/$MAX_OLLAMA"
done

# Wait for all background processes to complete
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Waiting for all models to complete..."
for pid in "${!running_models[@]}"; do
    wait "$pid"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Process $pid completed"
done

echo ""
echo "========================================"
echo "All Studies Complete!"
echo "========================================"
echo "Models: ${MODELS[@]}"
echo "Levels completed: 1, 2, 3, 4, 5"
echo ""
echo "Next steps:"
echo "1. View reports in reports/ directory"
echo "2. Run analysis for each model: python3 scripts/analyze_prompt_levels.py --model <model>"
echo "3. Compare with baseline: python3 scripts/compare_levels.py --model <model>"
echo ""
