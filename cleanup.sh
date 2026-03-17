#!/bin/bash

# AI Security Benchmark Cleanup Script
# Removes unnecessary logs, docs, and cache files
# Keeps: generated_*/, reports/, core project files

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if dry run
DRY_RUN=${1:-"--dry-run"}

if [ "$DRY_RUN" = "--dry-run" ]; then
    echo -e "${YELLOW}DRY RUN MODE - No files will be deleted${NC}"
    echo "Run with: ./cleanup.sh --execute to actually delete files"
    echo ""
fi

# Function to remove file/directory
remove_item() {
    local item=$1
    if [ -e "$item" ]; then
        if [ "$DRY_RUN" = "--execute" ]; then
            rm -rf "$item"
            echo -e "${RED}✓ Deleted:${NC} $item"
        else
            echo -e "${YELLOW}Would delete:${NC} $item"
        fi
    fi
}

echo "=== Cleaning up AI Security Benchmark ==="
echo ""

# 1. Remove backup directory (93MB!)
echo -e "${GREEN}[1/7] Removing backup directories...${NC}"
remove_item "reports_backup"

# 2. Remove cache files
echo -e "${GREEN}[2/7] Removing cache files...${NC}"
remove_item ".generation_cache.json"
remove_item "__pycache__"
remove_item "cache"
remove_item ".DS_Store"

# 3. Remove temporary files
echo -e "${GREEN}[3/7] Removing temporary files...${NC}"
remove_item ".temp_access_001.yaml"
remove_item ".temp_logic_002.yaml"
remove_item ".simple_prompt.txt"
remove_item ".test_prompt.txt"

# 4. Remove all log files
echo -e "${GREEN}[4/7] Removing log files...${NC}"
for log in *.log; do
    [ -e "$log" ] && remove_item "$log"
done

# 5. Remove dated documentation (JAN30, JAN31, etc.)
echo -e "${GREEN}[5/7] Removing dated documentation...${NC}"
for doc in *JAN30*.md *JAN31*.md *JAN_2026.md *20260*.md; do
    [ -e "$doc" ] && remove_item "$doc"
done

# 6. Remove duplicate/summary documentation
echo -e "${GREEN}[6/7] Removing duplicate summaries...${NC}"
REMOVE_DOCS=(
    "FINAL_*.md"
    "COMPLETE_*.md"
    "SESSION_*.md"
    "SUMMARY_*.md"
    "DETECTOR_FIXES_*.md"
    "DETECTOR_IMPROVEMENTS_*.md"
    "IMPROVEMENT_*.md"
    "IMPLEMENTATION_*.md"
    "ANALYSIS_*.md"
    "CHANGELOG.md"
    "ITERATION_*.md"
    "ROUND_*.md"
    "VERSION_*.md"
    "VALIDATION_*.md"
    "VERIFICATION_*.md"
    "BENCHMARK_*.md"
    "*_SUMMARY.md"
    "*_COMPLETE.md"
    "*_REPORT.md"
    "*_GUIDE.md"
)

for pattern in "${REMOVE_DOCS[@]}"; do
    for doc in $pattern; do
        # Keep README.md, USAGE.md, API_SETUP.md
        if [ -e "$doc" ] && [[ "$doc" != "README.md" ]] && [[ "$doc" != "USAGE.md" ]] && [[ "$doc" != "API_SETUP.md" ]]; then
            remove_item "$doc"
        fi
    done
done

# 7. Remove old test/analysis scripts
echo -e "${GREEN}[7/7] Removing old analysis scripts...${NC}"
OLD_SCRIPTS=(
    "analyze_chatgpt_feedback.py"
    "analyze_controversial.py"
    "analyze_false_positives.py"
    "analyze_fp_fn_across_models.py"
    "analyze_multiple_reports.py"
    "analyze_report_simple.py"
    "analyze_report_with_openai.py"
    "analyze_vulnerabilities.py"
    "analyze_xxe_002.py"
    "compare_implementations.py"
    "compare_models_on_variations.py"
    "compare_results.py"
    "examine_controversial_details.py"
    "fix_model_names.py"
    "generate_comparison_report.py"
    "generate_comprehensive_html.py"
    "generate_enhanced_prompts.py"
    "generate_missing_code.py"
    "generate_super_enhanced_prompts.py"
    "get_chatgpt_feedback.py"
    "improvement_rounds.py"
    "investigate_controversial_with_insight.py"
    "investigate_test.py"
    "multi_tier_analysis_all.py"
    "reanalyze_with_improved_detector.py"
    "regenerate_improved_prompts.py"
    "test_detector_fixes.py"
    "test_variations.py"
    "test_variations2.py"
    "verify_reports.py"
    "batch_compare.sh"
    "ollama_utils.sh"
    "quick_test.sh"
    "regenerate_all_reports.sh"
    "run_all_benchmarks.py"
    "run_all_models.sh"
    "run_all_super_enhanced.sh"
    "run_full_comparison.py"
    "test_all_openai_models.sh"
    "verify_xss_fix.sh"
)

for script in "${OLD_SCRIPTS[@]}"; do
    [ -e "$script" ] && remove_item "$script"
done

# Remove old test directories
remove_item "model_comparison_output"
remove_item "test_variations_output"
remove_item "test_variations_output2"

# Remove various test data files
for file in *_results.json *_output.log test_*.py test_*.js test_*.yaml; do
    if [ -e "$file" ]; then
        remove_item "$file"
    fi
done

# Remove external dependencies that might have been copied in
# PRESERVED: Keeping pairingfuzz and PyJFuzz
# remove_item "pairingfuzz"
# remove_item "PyJFuzz"

echo ""
echo "=== Summary ==="
if [ "$DRY_RUN" = "--execute" ]; then
    echo -e "${GREEN}Cleanup complete!${NC}"
else
    echo -e "${YELLOW}Dry run complete. No files were deleted.${NC}"
    echo "To actually delete files, run: ${GREEN}./cleanup.sh --execute${NC}"
fi

echo ""
echo "=== Preserved ==="
echo "✓ All generated_*/ directories (AI model outputs)"
echo "✓ reports/ directory"
echo "✓ prompts/ directory"
echo "✓ tests/ directory"
echo "✓ utils/ directory"
echo "✓ Core scripts: runner.py, html_report.py, auto_benchmark.py, etc."
echo "✓ README.md, USAGE.md, API_SETUP.md"
echo "✓ requirements.txt"
