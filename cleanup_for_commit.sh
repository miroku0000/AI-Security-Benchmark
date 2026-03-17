#!/bin/bash
# Cleanup script to prepare repository for commit
# Removes outdated documentation and old reports

set -e

YELLOW='\033[1;33m'
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

DRY_RUN=${1:-"--dry-run"}

if [ "$DRY_RUN" = "--dry-run" ]; then
    echo -e "${YELLOW}DRY RUN MODE - No files will be deleted${NC}"
    echo "Run with: ./cleanup_for_commit.sh --execute to actually delete files"
    echo ""
fi

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

echo "==================================================================="
echo "Cleanup for Git Commit - AI Security Benchmark"
echo "==================================================================="
echo ""

# 1. Remove outdated session/analysis documentation
echo -e "${GREEN}[1/6] Removing outdated session documentation...${NC}"
REMOVE_DOCS=(
    "ADDITIONAL_UNDETECTED_VULNERABILITIES.md"
    "BANDIT_FALSE_POSITIVE_ANALYSIS.md"
    "BENCHMARK_SUMMARY.md"
    "BENCHMARK_VS_SAST_COMPARISON.md"
    "BUSINESS_LOGIC_DETECTOR_IMPLEMENTATION.md"
    "CLAUDE_4_BENCHMARK_RESULTS.md"
    "CLAUDE_4_MODELS.md"
    "CLEAN_RETEST_PLAN.md"
    "COMPREHENSIVE_RESULTS_PERCENTILE.md"
    "controversial_tests_summary.md"
    "defense_in_depth_proposal.md"
    "DETECTOR_FIX_PRIORITIES.md"
    "DETECTOR_FIX_PRIORITY.md"
    "detector_improvements_summary.md"
    "FAILED_GENERATION_TRACKING.md"
    "FALSE_POSITIVE_NEGATIVE_ANALYSIS.md"
    "FALSE_POSITIVE_REEVALUATION.md"
    "FILE_OPERATION_COVERAGE.md"
    "FINAL_SUMMARY.md"
    "FP_ANALYSIS_FINAL_FINDINGS.md"
    "ground_truth_conclusion.md"
    "HTML_REPORTS.md"
    "HTML_SECURITY.md"
    "IMPROVEMENTS_1234_RESULTS.md"
    "INTELLIGENT_TIMEOUT_UPDATE.md"
    "ITERATIONS_11_20.md"
    "ITERATIVE_REFINEMENT_RESULTS.md"
    "ITERATIVE_REFINEMENT_SUCCESS.md"
    "JWT_ITERATIVE_REFINEMENT_SUCCESS.md"
    "MISSING_CODE_ANALYSIS.md"
    "MISSING_CODE_ROOT_CAUSE_ANALYSIS.md"
    "missing_vulnerabilities.md"
    "MODEL_TRACKING.md"
    "MODELS_TO_BENCHMARK.md"
    "NEW_DETECTORS_INTEGRATION.md"
    "OPENAI_ANALYSIS_IMPROVEMENTS_JAN2026.md"
    "OPENAI_IMPROVEMENTS_SESSION.md"
    "OPENAI_MODEL_EXPANSION.md"
    "OPENAI_PROMPT_IMPROVEMENTS.md"
    "OPTION_INJECTION.md"
    "path_002_analysis.md"
    "path_002_ground_truth.md"
    "PERMANENT_DETECTOR_FIXES_CONFIRMATION.md"
    "PLACEHOLDER_DETECTION.md"
    "PODMAN_SAST_ANALYSIS.md"
    "PROMPT_FIXES_APPLIED.md"
    "PROMPT_FIXES_REQUIRED.md"
    "PROMPT_IMPROVEMENTS_ACCESS_LOGIC.md"
    "PROMPT_SECURITY_ANALYSIS.md"
    "PROMPTS_WITH_MULTI_DETECTION.md"
    "README_MISTRAL_VERIFICATION.md"
    "README_OPENAI_ANALYSIS.md"
    "README_PIPELINE.md"
    "REPORT_FORMAT_ISSUES_RESOLVED.md"
    "RETEST_PLAN.md"
    "RUN_OPENAI_BENCHMARKS.md"
    "RUNNING_ANALYSIS_INFO.md"
    "sast_accuracy_chatgpt-4o-latest_20260208_094200_report.md"
    "SAST_ANALYSIS_RESULTS.md"
    "SAST_ONLY_FINDINGS_ANALYSIS.md"
    "SEMGREP_ENHANCEMENT_OPPORTUNITIES.md"
    "SEND_FROM_DIRECTORY_VULN.md"
    "SESSION_SUMMARY.md"
    "STATIC_ANALYSIS_SUMMARY.md"
    "SUMMARY.md"
    "TAR_EXTRACTION_VULN.md"
    "UNDETECTED_VULNERABILITIES.md"
    "xml2js_ground_truth_research.md"
    "xxe_002_final_analysis.md"
)

for doc in "${REMOVE_DOCS[@]}"; do
    remove_item "$doc"
done

# 2. Remove old log files
echo -e "${GREEN}[2/6] Removing log files...${NC}"
remove_item "test_run.log"
remove_item "nohup.out"
for log in *.log; do
    [ -e "$log" ] && remove_item "$log"
done

# 3. Remove old JSON data files
echo -e "${GREEN}[3/6] Removing old analysis JSON files...${NC}"
remove_item "all_false_positives_for_review.json"
remove_item "bandit_false_positives.json"
remove_item "fp_review_results.json"
remove_item "sast_accuracy_chatgpt-4o-latest_20260208_094200.json"
remove_item "sast_accuracy_chatgpt-4o-latest_CORRECTED.json"
remove_item "sast_accuracy_chatgpt-4o-latest_UPDATED.json"
remove_item "verification_hypothesis_test.json"

# 4. Remove old report files (non-208point)
echo -e "${GREEN}[4/6] Cleaning up old report files...${NC}"
# Keep: *_208point_*.json, HTML reports in reports/html/, and benchmark_report.*
for report in reports/*.json; do
    if [ -e "$report" ]; then
        # Keep 208-point reports and benchmark_report.json
        if [[ "$report" == *"208point"* ]] || [[ "$report" == *"benchmark_report.json"* ]]; then
            continue
        fi
        remove_item "$report"
    fi
done

# Remove old HTML reports not in html/ subdirectory
for html in reports/*.html; do
    if [ -e "$html" ]; then
        # Keep benchmark_report.html
        if [[ "$html" == *"benchmark_report.html"* ]]; then
            continue
        fi
        remove_item "$html"
    fi
done

# 5. Remove cache and temp files
echo -e "${GREEN}[5/6] Removing cache and temporary files...${NC}"
remove_item ".generation_cache.json"
remove_item "__pycache__"
remove_item ".DS_Store"

# 6. Remove old test directories and files
echo -e "${GREEN}[6/6] Removing old test files...${NC}"
remove_item "FILES_UPDATED.txt"
remove_item "FILES.txt"
remove_item "test_claude_sonnet_4_5"

echo ""
echo "==================================================================="
echo "Cleanup Summary"
echo "==================================================================="
if [ "$DRY_RUN" = "--execute" ]; then
    echo -e "${GREEN}✅ Cleanup complete!${NC}"
else
    echo -e "${YELLOW}Dry run complete. No files were deleted.${NC}"
    echo "To actually delete files, run: ${GREEN}./cleanup_for_commit.sh --execute${NC}"
fi
echo ""
echo "==================================================================="
echo "Files Preserved:"
echo "==================================================================="
echo "📄 Essential Documentation:"
echo "   ✓ README.md"
echo "   ✓ API_SETUP.md"
echo "   ✓ USAGE.md"
echo "   ✓ QUICKSTART.md"
echo "   ✓ OLLAMA_QUICKSTART.md"
echo ""
echo "📖 Configuration & Guides:"
echo "   ✓ DETECTOR_GUIDELINES.md"
echo "   ✓ SAST_CONFIGURATION_GUIDE.md"
echo "   ✓ PIPELINE_GUIDE.md"
echo "   ✓ QUICK_REFERENCE.md"
echo ""
echo "📊 Current Results:"
echo "   ✓ ACTUAL_MODELS_INVENTORY.md (needs update)"
echo "   ✓ COMPLETE_MODEL_RESULTS.md"
echo "   ✓ COMPREHENSIVE_RESULTS_208POINT.md"
echo ""
echo "📁 Directories:"
echo "   ✓ generated_*/ (all model code)"
echo "   ✓ reports/html/ (HTML reports)"
echo "   ✓ reports/*208point*.json (current benchmark data)"
echo "   ✓ prompts/"
echo "   ✓ tests/"
echo "   ✓ utils/"
echo ""
