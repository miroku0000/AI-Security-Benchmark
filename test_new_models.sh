#!/bin/bash
# Script to test and benchmark the latest AI models
# Keeps existing data and adds new models

set -e

echo "======================================================================"
echo "Testing Latest AI Models - Adding to Existing Benchmark"
echo "======================================================================"
echo ""

# Latest OpenAI Models (confirmed available from API)
NEW_OPENAI_MODELS=(
    "gpt-5.4"              # Latest GPT-5 flagship (March 5, 2026)
    "gpt-5.4-mini"         # Latest GPT-5 mini (March 17, 2026)
    "gpt-5.4-pro"          # Latest GPT-5 pro (March 5, 2026)
    "o4-mini"              # Latest o-series reasoning (April 16, 2026)
)

# Latest Anthropic Models (need to verify availability)
NEW_ANTHROPIC_MODELS=(
    "claude-3-5-sonnet-20241022"  # Known working model ID
    "claude-3-opus-20240229"       # Try opus
)

echo "New Models to Test:"
echo "-------------------"
echo "OpenAI (${#NEW_OPENAI_MODELS[@]} models):"
for model in "${NEW_OPENAI_MODELS[@]}"; do
    echo "  • $model"
done
echo ""
echo "Anthropic (${#NEW_ANTHROPIC_MODELS[@]} models):"
for model in "${NEW_ANTHROPIC_MODELS[@]}"; do
    echo "  • $model"
done
echo ""
echo "======================================================================"
echo ""

# Function to test and benchmark a model
test_model() {
    local model="$1"
    local model_safe=$(echo "$model" | sed 's/:/_/g')

    echo "Testing: $model"
    echo "-------------------"

    # Step 1: Generate code (uses cache if already exists)
    echo "Step 1: Generating code..."
    if python3 code_generator.py \
        --model "$model" \
        --output "generated_${model_safe}"; then
        echo "✅ Code generation complete"
    else
        echo "❌ Code generation failed for $model"
        return 1
    fi

    # Step 2: Run benchmark
    echo "Step 2: Running benchmark..."
    if python3 runner.py \
        --model "$model" \
        --code-dir "generated_${model_safe}"; then
        echo "✅ Benchmark complete"
    else
        echo "❌ Benchmark failed for $model"
        return 1
    fi

    echo ""
    return 0
}

# Test OpenAI models
echo "======================================================================"
echo "Testing OpenAI Models"
echo "======================================================================"
echo ""

for model in "${NEW_OPENAI_MODELS[@]}"; do
    test_model "$model"
done

# Test Anthropic models
echo "======================================================================"
echo "Testing Anthropic Models"
echo "======================================================================"
echo ""

for model in "${NEW_ANTHROPIC_MODELS[@]}"; do
    test_model "$model"
done

# Regenerate comparison report with all models
echo "======================================================================"
echo "Regenerating Comparison Report"
echo "======================================================================"
echo ""

python3 generate_html_reports.py

echo "======================================================================"
echo "All Tests Complete!"
echo "======================================================================"
echo ""
echo "View the updated comparison report:"
echo "  open reports/html/index.html"
echo ""
