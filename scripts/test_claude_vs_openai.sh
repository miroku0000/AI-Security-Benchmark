#!/bin/bash
# Test Claude vs OpenAI models (Codex successors) at various temperatures

echo "========================================================================"
echo "Testing Claude vs OpenAI Code Models at Multiple Temperatures"
echo "========================================================================"
echo ""

# Temperature values to test
TEMPS=(0.0 0.2 0.5 0.7)

# Claude models
CLAUDE_MODELS=(
    "claude-opus-4-6"
    "claude-sonnet-4-5"
)

# OpenAI models (Codex successors)
OPENAI_MODELS=(
    "gpt-3.5-turbo"
    "gpt-4"
    "gpt-4o"
)

echo "This will test:"
echo "  - 2 Claude models"
echo "  - 3 OpenAI models (Codex successors)"
echo "  - At 4 temperature settings each"
echo "  - Total: 20 benchmark runs"
echo ""
read -p "Continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]
then
    echo "Cancelled."
    exit 0
fi

# Test Claude models
echo ""
echo "========================================================================"
echo "PHASE 1: Testing Claude Models"
echo "========================================================================"
for model in "${CLAUDE_MODELS[@]}"; do
    for temp in "${TEMPS[@]}"; do
        echo ""
        echo ">>> Testing $model at temperature $temp"
        python3 auto_benchmark.py --model "$model" --temperature "$temp" --retries 3
    done
done

# Test OpenAI models (Codex successors)
echo ""
echo "========================================================================"
echo "PHASE 2: Testing OpenAI Models (Codex Successors)"
echo "========================================================================"
for model in "${OPENAI_MODELS[@]}"; do
    for temp in "${TEMPS[@]}"; do
        echo ""
        echo ">>> Testing $model at temperature $temp"
        python3 auto_benchmark.py --model "$model" --temperature "$temp" --retries 3
    done
done

# Generate comparison analysis
echo ""
echo "========================================================================"
echo "PHASE 3: Generating Temperature Impact Analysis"
echo "========================================================================"
echo ""
for model in "${CLAUDE_MODELS[@]}" "${OPENAI_MODELS[@]}"; do
    echo "Analyzing $model..."
    python3 analysis/analyze_temperature_impact.py --model "$model" --output "analysis/temp_study_${model}.txt"
done

echo ""
echo "========================================================================"
echo "COMPLETE!"
echo "========================================================================"
echo ""
echo "Results saved in:"
echo "  - output/<model>_temp<X>/ directories"
echo "  - reports/<model>_temp<X>_208point_*.json"
echo "  - analysis/temp_study_<model>.txt"
echo ""
echo "To view comprehensive analysis:"
echo "  python3 analysis/analyze_temperature_impact.py"
