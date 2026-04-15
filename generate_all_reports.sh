#!/bin/bash

# Generate comprehensive reports for all base models
# This script runs analysis and generates JSON + Markdown reports

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting comprehensive report generation for all models..."

# List of all base models
MODELS=(
    "claude-code"
    "claude-opus-4-6"
    "claude-sonnet-4-5"
    "codegemma"
    "codellama"
    "codex"
    "codex-app-no-skill"
    "codex-app-security-skill"
    "cursor"
    "deepseek-coder"
    "deepseek-coder_6.7b-instruct"
    "gemini-2.5-flash"
    "gpt-3.5-turbo"
    "gpt-4"
    "gpt-4o"
    "gpt-4o-mini"
    "gpt-5.2"
    "gpt-5.4"
    "gpt-5.4-mini"
    "llama3.1"
    "mistral"
    "o1"
    "o3"
    "o3-mini"
    "qwen2.5-coder"
    "qwen2.5-coder_14b"
    "starcoder2"
)

# Create reports directory
mkdir -p reports logs

# Counter for progress
TOTAL=${#MODELS[@]}
COMPLETED=0
FAILED=0

# Process each model
for MODEL in "${MODELS[@]}"; do
    COMPLETED=$((COMPLETED + 1))
    echo ""
    echo "========================================================================"
    echo "[$COMPLETED/$TOTAL] Processing model: $MODEL"
    echo "========================================================================"
    
    # Check if output directory exists
    if [ ! -d "output/$MODEL" ]; then
        echo "⚠️  WARNING: output/$MODEL directory not found, skipping..."
        FAILED=$((FAILED + 1))
        continue
    fi
    
    # Check if output directory has files
    FILE_COUNT=$(find "output/$MODEL" -type f | wc -l | tr -d ' ')
    if [ "$FILE_COUNT" -eq "0" ]; then
        echo "⚠️  WARNING: output/$MODEL is empty, skipping..."
        FAILED=$((FAILED + 1))
        continue
    fi
    
    echo "📁 Found $FILE_COUNT files in output/$MODEL"
    
    # Run analysis and generate reports
    echo "🔍 Running security analysis..."
    python3 runner.py \
        --code-dir "output/$MODEL" \
        --output "reports/${MODEL}_analysis.json" \
        --model "$MODEL" \
        --temperature 0.0 \
        2>&1 | tee "logs/${MODEL}_report_generation.log"
    
    # Check if analysis succeeded
    if [ $? -eq 0 ] && [ -f "reports/${MODEL}_analysis.json" ]; then
        echo "✅ Report generated: reports/${MODEL}_analysis.json"
    else
        echo "❌ Failed to generate report for $MODEL"
        FAILED=$((FAILED + 1))
    fi
    
    echo ""
done

echo ""
echo "========================================================================"
echo "Report Generation Summary"
echo "========================================================================"
echo "Total models: $TOTAL"
echo "Successfully processed: $((TOTAL - FAILED))"
echo "Failed/Skipped: $FAILED"
echo ""
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Report generation complete!"
echo ""

# List generated reports
echo "Generated reports:"
ls -lh reports/*_analysis.json 2>/dev/null | awk '{print $9, "("$5")"}'

