#!/bin/bash
#
# Simple re-analysis script for all models
#

echo "======================================================================"
echo "Multi-Language Detector Re-Analysis - Simple Version"
echo "======================================================================"
echo "Started: $(date)"
echo ""

# Change to benchmark directory
cd /Users/randy.flood/Documents/AI_Security_Benchmark

# Counter
total=0
success=0
failed=0

# Function to analyze one directory
analyze_dir() {
    local dir="$1"
    local name=$(basename "$dir")

    echo "Analyzing: $name"

    python3 runner.py \
        --code-dir "$dir" \
        --output "reports/${name}_208point_$(date +%Y%m%d).json" \
        --model "$name" \
        2>&1 | grep -E "(ANALYZING|VULNERABLE|SECURE|SUCCESS|FAILED|Error)"

    if [ $? -eq 0 ]; then
        echo "  ✓ Success: $name"
        ((success++))
    else
        echo "  ✗ Failed: $name"
        ((failed++))
    fi

    ((total++))
    echo ""
}

# Baseline models
echo "Phase 1: Baseline Models"
echo "----------------------------------------------------------------------"
for dir in output/claude-{code,opus-4-6,sonnet-4-5} output/gpt-{3.5-turbo,4,4o,4o-mini,5.2,5.4,5.4-mini} output/{codellama,deepseek-coder,codegemma,qwen2.5-coder,starcoder2,llama3.1,mistral,gemini-2.5-flash} output/{o1,o3,o3-mini,cursor} output/codex-app output/deepseek-coder_6.7b-instruct output/qwen2.5-coder_14b; do
    if [ -d "$dir" ]; then
        analyze_dir "$dir"
    fi
done

# Temperature models
echo ""
echo "Phase 2: Temperature Study Models"
echo "----------------------------------------------------------------------"
for dir in output/*_temp*; do
    if [ -d "$dir" ]; then
        analyze_dir "$dir"
    fi
done

# Level models
echo ""
echo "Phase 3: Prompt Level Study Models"
echo "----------------------------------------------------------------------"
for dir in output/*_level*; do
    if [ -d "$dir" ]; then
        analyze_dir "$dir"
    fi
done

# Summary
echo "======================================================================"
echo "Re-Analysis Complete"
echo "======================================================================"
echo "Total: $total"
echo "Success: $success"
echo "Failed: $failed"
echo "Finished: $(date)"
echo "======================================================================"
