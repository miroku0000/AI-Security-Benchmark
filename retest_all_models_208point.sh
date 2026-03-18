#!/bin/bash
# Retest all models with existing code on 208-point benchmark
# This ensures all models are tested with the current benchmark scale

set -e

YELLOW='\033[1;33m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "=================================================================="
echo "Retest All Models on 208-Point Benchmark Scale"
echo "=================================================================="
echo ""
echo "This script will:"
echo "  1. Find all models with generated code (66 files)"
echo "  2. Run the 208-point benchmark on existing code"
echo "  3. Save reports with standardized naming"
echo "  4. Generate updated HTML comparison"
echo ""
echo -e "${YELLOW}Note: This reuses existing code - no API calls needed!${NC}"
echo ""

# Function to count files in a directory
count_files() {
    local dir=$1
    if [ -d "$dir" ]; then
        ls "$dir" 2>/dev/null | wc -l | tr -d ' '
    else
        echo "0"
    fi
}

# Function to run benchmark on existing code
benchmark_model() {
    local model_name=$1
    local code_dir=$2
    local file_count=$(count_files "$code_dir")

    echo -e "${BLUE}Testing: $model_name${NC}"
    echo "  Code directory: $code_dir"
    echo "  Files: $file_count"

    # Skip if directory doesn't exist or is incomplete
    if [ ! -d "$code_dir" ]; then
        echo -e "  ${YELLOW}⊘ Skipped: Directory not found${NC}"
        echo ""
        return
    fi

    if [ "$file_count" -lt "66" ]; then
        echo -e "  ${YELLOW}⊘ Skipped: Incomplete code ($file_count/66 files)${NC}"
        echo ""
        return
    fi

    # Run benchmark
    echo "  Running benchmark..."
    if python3 runner.py --model "$model_name" --code-dir "$code_dir" 2>&1 | tail -10; then
        # Save with timestamped name
        timestamp=$(date +%Y%m%d_%H%M%S)
        cp reports/benchmark_report.json "reports/${model_name}_208point_${timestamp}.json"
        echo -e "  ${GREEN}✓ Complete: reports/${model_name}_208point_${timestamp}.json${NC}"
    else
        echo -e "  ${YELLOW}✗ Failed to benchmark${NC}"
    fi

    echo ""
}

# Find all models with generated code
echo "=================================================================="
echo "Scanning for Models with Generated Code"
echo "=================================================================="
echo ""

models_tested=0
models_skipped=0

for dir in generated_*/; do
    # Extract model name from directory
    model_name=$(basename "$dir" | sed 's/^generated_//')

    # Check if complete
    file_count=$(count_files "$dir")

    if [ "$file_count" -ge "66" ]; then
        benchmark_model "$model_name" "$dir"
        ((models_tested++))
    else
        echo -e "${YELLOW}⊘ Skipped: $model_name (incomplete: $file_count/66 files)${NC}"
        ((models_skipped++))
    fi
done

# Regenerate HTML reports
echo "=================================================================="
echo "Regenerating HTML Comparison Reports"
echo "=================================================================="
echo ""

python3 generate_html_reports.py

echo "=================================================================="
echo "Retest Complete!"
echo "=================================================================="
echo ""
echo "Summary:"
echo "  ✓ Models tested: $models_tested"
echo "  ⊘ Models skipped: $models_skipped"
echo ""
echo "View results:"
echo "  open reports/html/index.html"
echo ""
