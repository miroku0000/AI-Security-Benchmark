#!/bin/bash
# Multi-Level Security Prompt Study Runner
# Runs levels 1-5 for a specified model (Level 0 already exists as baseline)

set -e

MODEL=$1

if [ -z "$MODEL" ]; then
    echo "Usage: $0 <model_name>"
    echo ""
    echo "Example: $0 gpt-4o-mini"
    echo "         $0 deepseek-coder"
    echo "         $0 qwen2.5-coder"
    echo ""
    echo "Available models:"
    echo "  API Models: gpt-4o-mini, gpt-4o, claude-opus-4.6, claude-sonnet-4.5"
    echo "  Ollama Models: deepseek-coder, qwen2.5-coder, codellama, llama3.1"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

echo "========================================"
echo "Multi-Level Security Prompt Study"
echo "========================================"
echo "Model: $MODEL"
echo "Levels: 1-5 (140 prompts per level = 700 total)"
echo "========================================"
echo ""

# Check if Level 0 (baseline) exists
if [ ! -d "output/$MODEL" ]; then
    echo "WARNING: Level 0 (baseline) not found at output/$MODEL"
    echo "You should run baseline first:"
    echo "  python3 auto_benchmark.py --model $MODEL --all"
    echo ""
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Run levels 1-5
for level in 1 2 3 4 5; do
    echo ""
    echo "========================================"
    echo "Running Level $level"
    echo "========================================"

    OUTPUT_DIR="output/${MODEL}_level${level}"
    PROMPT_FILE="prompts/prompts_level${level}_security.yaml"

    if [ ! -f "$PROMPT_FILE" ]; then
        echo "ERROR: Prompt file not found: $PROMPT_FILE"
        exit 1
    fi

    # Generate code
    echo "Generating code..."
    python3 code_generator.py \
        --model "$MODEL" \
        --prompts "$PROMPT_FILE" \
        --output "$OUTPUT_DIR" \
        --retries 2 \
        --timeout 180 \
        2>&1 | tee "logs/${MODEL}_level${level}_generation.log"

    # Run security analysis
    echo ""
    echo "Running security analysis..."
    python3 runner.py \
        --code-dir "$OUTPUT_DIR" \
        --model "${MODEL}_level${level}" \
        2>&1 | tee "logs/${MODEL}_level${level}_analysis.log"

    echo ""
    echo "Level $level complete!"
    echo "Results: $OUTPUT_DIR"
    echo "Report: reports/${MODEL}_level${level}_*.html"
done

echo ""
echo "========================================"
echo "Study Complete!"
echo "========================================"
echo "Model: $MODEL"
echo "Levels completed: 1, 2, 3, 4, 5"
echo "Total prompts: 700 (140 × 5)"
echo ""
echo "Next steps:"
echo "1. View reports in reports/ directory"
echo "2. Run analysis: python3 scripts/analyze_prompt_levels.py --model $MODEL"
echo "3. Compare with baseline: python3 scripts/compare_levels.py --model $MODEL"
echo ""
