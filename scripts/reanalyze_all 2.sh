#!/bin/bash
#
# Re-analyze ALL model outputs with enhanced multi-language detectors
#
# This script re-runs security analysis on all existing model outputs now that
# we have comprehensive Go, Java, Rust, C#, and C/C++ detection capabilities.
#
# Usage:
#   bash reanalyze_all.sh                    # Run all analyses
#   bash reanalyze_all.sh --baseline-only    # Only baseline (non-temp) models
#   bash reanalyze_all.sh --temp-only        # Only temperature study models
#   bash reanalyze_all.sh --levels-only      # Only prompt level study models
#

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Track progress
TOTAL_COUNT=0
SUCCESS_COUNT=0
SKIP_COUNT=0
FAIL_COUNT=0

# Log file
LOG_FILE="logs/reanalysis_$(date +%Y%m%d_%H%M%S).log"
mkdir -p logs

echo -e "${BLUE}=====================================================================${NC}"
echo -e "${BLUE}Multi-Language Detector Re-Analysis${NC}"
echo -e "${BLUE}=====================================================================${NC}"
echo -e "Started: $(date)"
echo -e "Log file: ${LOG_FILE}"
echo -e "${BLUE}=====================================================================${NC}"
echo ""

# Function to run analysis on a directory
analyze_directory() {
    local dir=$1
    local model_name=$(basename "$dir")
    local output_dir="$dir"

    # Check if directory has code files
    local code_count=$(find "$output_dir" -maxdepth 1 \( -name "*.py" -o -name "*.js" -o -name "*.go" -o -name "*.java" -o -name "*.rs" -o -name "*.cs" -o -name "*.cpp" -o -name "*.c" \) 2>/dev/null | wc -l | tr -d ' ')

    if [ "$code_count" -eq 0 ]; then
        echo -e "${YELLOW}SKIP${NC} $model_name (no code files)"
        ((SKIP_COUNT++))
        return 0
    fi

    # Extract temperature if present
    local temp_value=""
    if [[ "$model_name" =~ _temp([0-9.]+)$ ]]; then
        temp_value="${BASH_REMATCH[1]}"
    fi

    # Determine report name with date
    local date_str=$(date +%Y%m%d)
    local report_name="${model_name}_208point_${date_str}"

    echo -e "${BLUE}ANALYZING${NC} $model_name ($code_count files)"

    # Build command
    local cmd="python3 runner.py --code-dir \"$output_dir\" --output \"reports/${report_name}.json\" --model \"$model_name\""

    # Add temperature if detected
    if [ -n "$temp_value" ]; then
        cmd="$cmd --temperature $temp_value"
    fi

    # Run analysis
    if eval "$cmd" >> "$LOG_FILE" 2>&1; then
        echo -e "${GREEN}SUCCESS${NC} $model_name → reports/${report_name}.json"
        ((SUCCESS_COUNT++))
    else
        echo -e "${RED}FAILED${NC} $model_name (see $LOG_FILE)"
        ((FAIL_COUNT++))
    fi

    ((TOTAL_COUNT++))
}

# Parse command line arguments
BASELINE_ONLY=false
TEMP_ONLY=false
LEVELS_ONLY=false

for arg in "$@"; do
    case $arg in
        --baseline-only)
            BASELINE_ONLY=true
            ;;
        --temp-only)
            TEMP_ONLY=true
            ;;
        --levels-only)
            LEVELS_ONLY=true
            ;;
    esac
done

# Find all output directories
OUTPUT_BASE="/Users/randy.flood/Documents/AI_Security_Benchmark/output"

# Baseline models (no _temp suffix, no _level suffix)
if [ "$TEMP_ONLY" = false ] && [ "$LEVELS_ONLY" = false ]; then
    echo -e "\n${BLUE}=====================================================================${NC}"
    echo -e "${BLUE}Phase 1: Baseline Models${NC}"
    echo -e "${BLUE}=====================================================================${NC}\n"

    for dir in "$OUTPUT_BASE"/*; do
        if [ -d "$dir" ]; then
            basename=$(basename "$dir")
            # Skip temp and level directories
            if [[ ! "$basename" =~ _temp ]] && [[ ! "$basename" =~ _level ]]; then
                analyze_directory "$dir"
            fi
        fi
    done
fi

# Temperature study models
if [ "$BASELINE_ONLY" = false ] && [ "$LEVELS_ONLY" = false ]; then
    echo -e "\n${BLUE}=====================================================================${NC}"
    echo -e "${BLUE}Phase 2: Temperature Study Models${NC}"
    echo -e "${BLUE}=====================================================================${NC}\n"

    for dir in "$OUTPUT_BASE"/*_temp*; do
        if [ -d "$dir" ]; then
            analyze_directory "$dir"
        fi
    done
fi

# Prompt level study models
if [ "$BASELINE_ONLY" = false ] && [ "$TEMP_ONLY" = false ]; then
    echo -e "\n${BLUE}=====================================================================${NC}"
    echo -e "${BLUE}Phase 3: Prompt Level Study Models${NC}"
    echo -e "${BLUE}=====================================================================${NC}\n"

    for dir in "$OUTPUT_BASE"/*_level*; do
        if [ -d "$dir" ]; then
            # Extract level number
            if [[ $(basename "$dir") =~ _level([0-9]+)$ ]]; then
                analyze_directory "$dir"
            fi
        fi
    done
fi

# Final summary
echo -e "\n${BLUE}=====================================================================${NC}"
echo -e "${BLUE}Re-Analysis Complete${NC}"
echo -e "${BLUE}=====================================================================${NC}"
echo -e "Total directories processed: $TOTAL_COUNT"
echo -e "${GREEN}Successful: $SUCCESS_COUNT${NC}"
echo -e "${YELLOW}Skipped: $SKIP_COUNT${NC}"
echo -e "${RED}Failed: $FAIL_COUNT${NC}"
echo -e "Finished: $(date)"
echo -e "Log file: ${LOG_FILE}"
echo -e "${BLUE}=====================================================================${NC}"

# Generate HTML reports for all JSON reports
echo -e "\n${BLUE}Generating HTML reports...${NC}"
python3 utils/generate_html_reports.py

echo -e "\n${GREEN}All re-analysis complete!${NC}"
echo -e "Reports available in: reports/"

# Exit with error code if any failures
if [ $FAIL_COUNT -gt 0 ]; then
    exit 1
fi

exit 0
