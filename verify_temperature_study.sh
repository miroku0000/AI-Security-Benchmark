#!/bin/bash

echo "========================================="
echo "Temperature Study Verification"
echo "========================================="
echo ""

TOTAL_RUNS=0
COMPLETE_RUNS=0
INCOMPLETE_RUNS=0

# All models and temperatures
OPENAI_MODELS="gpt-3.5-turbo gpt-4 gpt-4o gpt-4o-mini gpt-5.2 gpt-5.4 gpt-5.4-mini"
ANTHROPIC_MODELS="claude-opus-4-6 claude-sonnet-4-5"
GOOGLE_MODELS="gemini-2.5-flash"
OLLAMA_MODELS="codellama deepseek-coder deepseek-coder:6.7b-instruct starcoder2 codegemma mistral llama3.1 qwen2.5-coder qwen2.5-coder:14b"

TEMPS="0.0 0.5 0.7 1.0"

echo "Checking all model/temperature combinations..."
echo ""

for model in $OPENAI_MODELS $ANTHROPIC_MODELS $GOOGLE_MODELS $OLLAMA_MODELS; do
    model_dir=$(echo "$model" | tr ':' '_')
    
    for temp in $TEMPS; do
        ((TOTAL_RUNS++))
        output_dir="output/${model_dir}_temp${temp}"
        
        if [ -d "$output_dir" ]; then
            file_count=$(ls "$output_dir" 2>/dev/null | wc -l | tr -d ' ')
            if [ "$file_count" -eq 141 ]; then
                ((COMPLETE_RUNS++))
                echo "✓ ${model_dir}_temp${temp}: ${file_count}/141"
            else
                ((INCOMPLETE_RUNS++))
                echo "✗ ${model_dir}_temp${temp}: ${file_count}/141 (INCOMPLETE)"
            fi
        else
            ((INCOMPLETE_RUNS++))
            echo "✗ ${model_dir}_temp${temp}: MISSING"
        fi
    done
done

echo ""
echo "========================================="
echo "Summary"
echo "========================================="
echo "Total runs expected:  $TOTAL_RUNS"
echo "Complete (141/141):   $COMPLETE_RUNS"
echo "Incomplete/Missing:   $INCOMPLETE_RUNS"
echo ""

if [ $COMPLETE_RUNS -eq $TOTAL_RUNS ]; then
    echo "🎉 TEMPERATURE STUDY COMPLETE!"
    echo "All 76 model/temperature combinations have 141/141 files"
else
    echo "⚠ Temperature study incomplete"
    echo "Missing or incomplete: $INCOMPLETE_RUNS runs"
fi
echo ""
