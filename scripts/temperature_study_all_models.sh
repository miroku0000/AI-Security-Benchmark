#!/bin/bash
#
# Comprehensive Temperature Study Across All Models
# Tests all 23 temperature-supporting models at temperatures: 0.0, 0.2, 0.5, 0.7, 1.0
# Generates comparative security analysis reports
#
# Usage: ./scripts/temperature_study_all_models.sh [--skip-generation] [--report-only]
#

set -e  # Exit on error

# Configuration
TEMPS=(0.0 0.2 0.5 0.7 1.0)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_FILE="$PROJECT_DIR/temperature_study_$(date +%Y%m%d_%H%M%S).log"

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Parse arguments
SKIP_GENERATION=false
REPORT_ONLY=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-generation)
            SKIP_GENERATION=true
            shift
            ;;
        --report-only)
            REPORT_ONLY=true
            SKIP_GENERATION=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--skip-generation] [--report-only]"
            exit 1
            ;;
    esac
done

log() {
    echo -e "${BLUE}[$(date +%H:%M:%S)]${NC} $1" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "${GREEN}[$(date +%H:%M:%S)] ✓${NC} $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[$(date +%H:%M:%S)] ✗${NC} $1" | tee -a "$LOG_FILE"
}

log_warning() {
    echo -e "${YELLOW}[$(date +%H:%M:%S)] ⚠${NC} $1" | tee -a "$LOG_FILE"
}

# Model lists (23 models that support temperature)
# OpenAI GPT series (8 models)
OPENAI_MODELS=(
    "gpt-3.5-turbo"
    "gpt-4"
    "gpt-4o"
    "gpt-4o-mini"
    "chatgpt-4o-latest"
    "gpt-5.2"
    "gpt-5.4"
    "gpt-5.4-mini"
)

# Anthropic Claude (2 models)
CLAUDE_MODELS=(
    "claude-opus-4-6"
    "claude-sonnet-4-5"
)

# Google Gemini (1 model)
GEMINI_MODELS=(
    "gemini-2.5-flash"
)

# Ollama local models (9 models)
OLLAMA_MODELS=(
    "codellama"
    "deepseek-coder"
    "deepseek-coder:6.7b-instruct"
    "starcoder2"
    "codegemma"
    "mistral"
    "llama3.1"
    "qwen2.5-coder"
    "qwen2.5-coder:14b"
)

# Excluded models (do NOT support temperature)
EXCLUDED_MODELS=(
    "o1"
    "o3"
    "o3-mini"
)

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."

    # Check API keys
    if [ -z "$OPENAI_API_KEY" ]; then
        log_warning "OPENAI_API_KEY not set - OpenAI models will be skipped"
    else
        log_success "OPENAI_API_KEY found"
    fi

    if [ -z "$MYANTHROPIC_API_KEY" ]; then
        log_warning "MYANTHROPIC_API_KEY not set - Claude models will be skipped"
    else
        log_success "MYANTHROPIC_API_KEY found"
    fi

    if [ -z "$GEMINI_API_KEY" ]; then
        log_warning "GEMINI_API_KEY not set - Gemini models will be skipped"
    else
        log_success "GEMINI_API_KEY found"
    fi

    # Check Ollama
    if command -v ollama &> /dev/null; then
        log_success "Ollama found"
        # Check which Ollama models are available
        AVAILABLE_OLLAMA=$(ollama list 2>/dev/null | tail -n +2 | awk '{print $1}' | tr '\n' ' ')
        log "Available Ollama models: $AVAILABLE_OLLAMA"
    else
        log_warning "Ollama not found - local models will be skipped"
    fi

    # Check Python dependencies
    if python3 -c "import openai, anthropic, google.genai, ollama" 2>/dev/null; then
        log_success "All Python dependencies installed"
    else
        log_warning "Some Python dependencies missing - run: pip install -r requirements.txt"
    fi

    echo ""
}

# Test a single model at a single temperature
test_model_temperature() {
    local model=$1
    local temp=$2
    local provider=$3

    log "Testing ${YELLOW}${model}${NC} at temperature ${YELLOW}${temp}${NC}"

    # Set Anthropic key if testing Claude models
    if [ "$provider" = "claude" ]; then
        export ANTHROPIC_API_KEY=$MYANTHROPIC_API_KEY
    fi

    # Run benchmark with retries
    if python3 "$PROJECT_DIR/auto_benchmark.py" \
        --model "$model" \
        --temperature "$temp" \
        --retries 3 >> "$LOG_FILE" 2>&1; then
        log_success "Completed ${model} at temp ${temp}"
    else
        log_error "Failed ${model} at temp ${temp}"
    fi

    # Unset Anthropic key to avoid Claude Code conflicts
    if [ "$provider" = "claude" ]; then
        unset ANTHROPIC_API_KEY
    fi

    echo ""
}

# Run all tests
run_temperature_tests() {
    local total_tests=0
    local completed_tests=0

    # Calculate total tests
    total_tests=$((${#OPENAI_MODELS[@]} * ${#TEMPS[@]} + \
                   ${#CLAUDE_MODELS[@]} * ${#TEMPS[@]} + \
                   ${#GEMINI_MODELS[@]} * ${#TEMPS[@]} + \
                   ${#OLLAMA_MODELS[@]} * ${#TEMPS[@]}))

    echo ""
    echo "========================================================================"
    echo "COMPREHENSIVE TEMPERATURE STUDY"
    echo "========================================================================"
    echo "Models: 23 (OpenAI: 8, Claude: 2, Gemini: 1, Ollama: 9)"
    echo "Temperatures: ${TEMPS[*]}"
    echo "Total test runs: $total_tests"
    echo "Excluded models (no temp support): ${EXCLUDED_MODELS[*]}"
    echo "Log file: $LOG_FILE"
    echo "========================================================================"
    echo ""

    # Test OpenAI models
    if [ -n "$OPENAI_API_KEY" ]; then
        log "Starting OpenAI models (8 models x 5 temperatures = 40 tests)..."
        for model in "${OPENAI_MODELS[@]}"; do
            for temp in "${TEMPS[@]}"; do
                test_model_temperature "$model" "$temp" "openai"
                ((completed_tests++))
                log "Progress: $completed_tests/$total_tests tests completed"
            done
        done
    else
        log_warning "Skipping OpenAI models (no API key)"
    fi

    # Test Claude models
    if [ -n "$MYANTHROPIC_API_KEY" ]; then
        log "Starting Claude models (2 models x 5 temperatures = 10 tests)..."
        for model in "${CLAUDE_MODELS[@]}"; do
            for temp in "${TEMPS[@]}"; do
                test_model_temperature "$model" "$temp" "claude"
                ((completed_tests++))
                log "Progress: $completed_tests/$total_tests tests completed"
            done
        done
    else
        log_warning "Skipping Claude models (no API key)"
    fi

    # Test Gemini models
    if [ -n "$GEMINI_API_KEY" ]; then
        log "Starting Gemini models (1 model x 5 temperatures = 5 tests)..."
        for model in "${GEMINI_MODELS[@]}"; do
            for temp in "${TEMPS[@]}"; do
                test_model_temperature "$model" "$temp" "gemini"
                ((completed_tests++))
                log "Progress: $completed_tests/$total_tests tests completed"
            done
        done
    else
        log_warning "Skipping Gemini models (no API key)"
    fi

    # Test Ollama models (sequential to avoid resource exhaustion)
    if command -v ollama &> /dev/null; then
        log "Starting Ollama models (9 models x 5 temperatures = 45 tests)..."
        log "Note: Ollama models run sequentially to prevent resource exhaustion"
        for model in "${OLLAMA_MODELS[@]}"; do
            # Check if model is available
            if ollama list 2>/dev/null | grep -q "^${model}"; then
                for temp in "${TEMPS[@]}"; do
                    test_model_temperature "$model" "$temp" "ollama"
                    ((completed_tests++))
                    log "Progress: $completed_tests/$total_tests tests completed"
                done
            else
                log_warning "Ollama model '$model' not found - run: ollama pull $model"
            fi
        done
    else
        log_warning "Skipping Ollama models (ollama not installed)"
    fi

    log_success "All tests completed: $completed_tests/$total_tests"
}

# Generate temperature impact reports
generate_reports() {
    log "Generating temperature impact analysis reports..."

    REPORT_DIR="$PROJECT_DIR/reports/temperature_study_$(date +%Y%m%d)"
    mkdir -p "$REPORT_DIR"

    # Generate individual model reports
    log "Analyzing individual models..."

    ALL_MODELS=("${OPENAI_MODELS[@]}" "${CLAUDE_MODELS[@]}" "${GEMINI_MODELS[@]}" "${OLLAMA_MODELS[@]}")

    for model in "${ALL_MODELS[@]}"; do
        if python3 "$PROJECT_DIR/analysis/analyze_temperature_impact.py" \
            --model "$model" \
            --output "$REPORT_DIR/${model}_temperature_analysis.txt" 2>/dev/null; then
            log_success "Generated report for $model"
        else
            log_warning "Could not generate report for $model (may not have test data)"
        fi
    done

    # Generate comparative summary
    log "Generating comparative summary across all models..."

    SUMMARY_FILE="$REPORT_DIR/temperature_study_summary.txt"

    cat > "$SUMMARY_FILE" << 'EOF'
================================================================================
TEMPERATURE IMPACT ON CODE SECURITY - COMPREHENSIVE STUDY
================================================================================

This study tests how temperature parameter affects security vulnerability rates
across 23 AI models from 4 providers (OpenAI, Anthropic, Google, Ollama).

Temperatures tested: 0.0, 0.2, 0.5, 0.7, 1.0
Benchmark: 66 prompts across 10 vulnerability categories (208-point scale)

================================================================================
SUMMARY BY PROVIDER
================================================================================

EOF

    # Extract scores from JSON reports and summarize
    python3 << 'PYTHON_SCRIPT' >> "$SUMMARY_FILE"
import json
import os
from pathlib import Path
from collections import defaultdict

project_dir = Path("$PROJECT_DIR")
reports_dir = project_dir / "reports"

# Group results by provider and temperature
results = defaultdict(lambda: defaultdict(list))

# Scan all report files
for report_file in reports_dir.glob("*_208point_*.json"):
    try:
        with open(report_file) as f:
            data = json.load(f)
            model = data.get("model", "unknown")
            temp = data.get("temperature")
            score = data.get("score", 0)
            max_score = data.get("max_score", 208)
            percentage = (score / max_score * 100) if max_score > 0 else 0

            # Determine provider
            if any(x in model.lower() for x in ["gpt", "chatgpt"]) and not any(x in model.lower() for x in ["o1", "o3"]):
                provider = "OpenAI (GPT)"
            elif any(x in model.lower() for x in ["claude"]):
                provider = "Anthropic (Claude)"
            elif any(x in model.lower() for x in ["gemini"]):
                provider = "Google (Gemini)"
            elif any(x in model for x in ["codellama", "deepseek", "starcoder", "codegemma", "mistral", "llama", "qwen"]):
                provider = "Ollama (Local)"
            else:
                continue

            if temp is not None:
                results[provider][temp].append({
                    "model": model,
                    "score": score,
                    "percentage": percentage
                })
    except Exception as e:
        continue

# Print summary
for provider in sorted(results.keys()):
    print(f"\n{provider}")
    print("=" * 80)
    print(f"{'Temperature':<15} {'Avg Score':<15} {'Avg %':<15} {'Models Tested':<15}")
    print("-" * 80)

    for temp in sorted(results[provider].keys()):
        models = results[provider][temp]
        avg_score = sum(m["score"] for m in models) / len(models)
        avg_pct = sum(m["percentage"] for m in models) / len(models)
        count = len(models)

        print(f"{temp:<15.1f} {avg_score:<15.1f} {avg_pct:<15.1f}% {count:<15}")

    # Best and worst temperature for this provider
    all_temps = []
    for temp, models in results[provider].items():
        avg_pct = sum(m["percentage"] for m in models) / len(models)
        all_temps.append((temp, avg_pct))

    if all_temps:
        all_temps.sort(key=lambda x: x[1], reverse=True)
        best_temp, best_pct = all_temps[0]
        worst_temp, worst_pct = all_temps[-1]
        print(f"\nBest temperature:  {best_temp} ({best_pct:.1f}%)")
        print(f"Worst temperature: {worst_temp} ({worst_pct:.1f}%)")
        print(f"Temperature impact: {abs(best_pct - worst_pct):.1f} percentage points")

print("\n" + "=" * 80)
print("KEY FINDINGS")
print("=" * 80)
print()
print("See individual model reports in:", reports_dir / "temperature_study_*")
print()
PYTHON_SCRIPT

    log_success "Comparative summary saved to $SUMMARY_FILE"

    # Generate HTML reports
    log "Generating HTML reports..."
    if python3 "$PROJECT_DIR/utils/generate_html_reports.py" >> "$LOG_FILE" 2>&1; then
        log_success "HTML reports generated"
    else
        log_warning "HTML report generation encountered issues"
    fi

    echo ""
    echo "========================================================================"
    echo "REPORTS GENERATED"
    echo "========================================================================"
    echo "Summary report:     $SUMMARY_FILE"
    echo "Individual reports: $REPORT_DIR/"
    echo "HTML reports:       $PROJECT_DIR/reports/html/index.html"
    echo "Full log:           $LOG_FILE"
    echo "========================================================================"
    echo ""
    echo "View HTML reports:"
    echo "  open $PROJECT_DIR/reports/html/index.html"
    echo ""
    echo "View summary:"
    echo "  cat $SUMMARY_FILE"
    echo ""
}

# Main execution
main() {
    cd "$PROJECT_DIR"

    log "Temperature Study Started"
    log "Study ID: $(date +%Y%m%d_%H%M%S)"

    check_prerequisites

    if [ "$REPORT_ONLY" = true ]; then
        log "Report-only mode: Skipping test execution"
        generate_reports
        exit 0
    fi

    if [ "$SKIP_GENERATION" = false ]; then
        START_TIME=$(date +%s)
        run_temperature_tests
        END_TIME=$(date +%s)
        DURATION=$((END_TIME - START_TIME))
        log_success "Test execution completed in ${DURATION}s"
    else
        log "Skipping test execution (--skip-generation)"
    fi

    generate_reports

    log_success "Temperature study complete!"
}

main
