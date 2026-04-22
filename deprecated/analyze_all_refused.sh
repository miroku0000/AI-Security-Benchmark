#!/bin/bash
#
# Analyze refused tests for all model directories
#
# Usage: ./analyze_all_refused.sh [output_directory]
#

OUTPUT_DIR="${1:-reports/refused_analysis}"

mkdir -p "$OUTPUT_DIR"

echo "Analyzing refused tests for all models..."
echo "Output directory: $OUTPUT_DIR"
echo ""

# Find all benchmark reports
for report in reports/benchmark_report*.json output/*/reports/benchmark_report.json; do
    if [ ! -f "$report" ]; then
        continue
    fi

    # Extract model name from path
    if [[ "$report" =~ output/([^/]+)/reports ]]; then
        model_name="${BASH_REMATCH[1]}"
        code_dir="output/$model_name"
    elif [[ "$report" == "reports/benchmark_report.json" ]]; then
        # Default report - try to infer from code dir
        model_name="unknown"
        code_dir="generated"
    else
        continue
    fi

    echo "Processing: $model_name"
    echo "  Report: $report"
    echo "  Code dir: $code_dir"

    # Run analysis
    python3 analyze_refused_tests.py \
        --report "$report" \
        --code-dir "$code_dir" \
        --output "$OUTPUT_DIR/${model_name}_refused_analysis.txt" \
        --json "$OUTPUT_DIR/${model_name}_refused_analysis.json"

    echo ""
done

echo "Analysis complete!"
echo "Results saved to: $OUTPUT_DIR/"
