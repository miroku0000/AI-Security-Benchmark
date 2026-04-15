#!/bin/bash

echo "========================================="
echo "Regenerating Temperature Study Reports"
echo "140 prompts (removed rust_013)"
echo "========================================="
echo ""

# All models tested at 4 temperatures
OPENAI_MODELS="gpt-3.5-turbo gpt-4 gpt-4o gpt-4o-mini gpt-5.2 gpt-5.4 gpt-5.4-mini"
ANTHROPIC_MODELS="claude-opus-4-6 claude-sonnet-4-5"
GOOGLE_MODELS="gemini-2.5-flash"
OLLAMA_MODELS="codellama deepseek-coder deepseek-coder:6.7b-instruct starcoder2 codegemma mistral llama3.1 qwen2.5-coder qwen2.5-coder:14b"

TEMPS="0.0 0.5 0.7 1.0"

TOTAL=0
COMPLETED=0

for model in $OPENAI_MODELS $ANTHROPIC_MODELS $GOOGLE_MODELS $OLLAMA_MODELS; do
    model_dir=$(echo "$model" | tr ':' '_')
    
    for temp in $TEMPS; do
        ((TOTAL++))
        output_dir="output/${model_dir}_temp${temp}"
        report_name="${model_dir}_temp${temp}_208point_$(date +%Y%m%d)"
        
        echo "[$COMPLETED/$TOTAL] Testing ${model_dir} at temp ${temp}..."
        
        # Run benchmark (using existing code, just regenerate reports)
        python3 auto_benchmark.py \
            --model "$model" \
            --temperature "$temp" \
            --output "$output_dir" \
            --report-name "$report_name" \
            > "logs/${report_name}.log" 2>&1
        
        if [ $? -eq 0 ]; then
            ((COMPLETED++))
            echo "  ✓ Complete: reports/${report_name}.html"
        else
            echo "  ✗ Failed"
        fi
    done
done

echo ""
echo "========================================="
echo "Temperature Study Reports Complete"
echo "========================================="
echo "Completed: $COMPLETED/$TOTAL"
echo ""
