#!/bin/bash

# Create directories if they don't exist
mkdir -p docs/studies
mkdir -p scripts/cleanup

echo "=== Moving documentation files to docs/ ==="

# Study/research documentation
for file in \
    ALL_STUDIES_COMPLETE_STATUS.md \
    MULTI_LEVEL_REPORTS_REGENERATED.md \
    WHITEPAPER_ASSERTIONS_VERIFIED.md \
    VERIFICATION_SUMMARY.md \
    WHITEPAPER_VERIFICATION_STATUS.md \
    FINAL_MULTI_LEVEL_RESULTS.md \
    MULTI_LEVEL_STUDY_STATUS.md \
    LEVEL_4_VALIDATION_RESULTS.md \
    MULTI_LEVEL_EXECUTION_PLAN.md \
    MULTI_LEVEL_PROMPTS_GENERATED.md \
    PROMPT_LEVELS_STUDY_PLAN.md \
    TEMPERATURE_STUDY_COMPLETE.md \
    FIXED_TEMPERATURE_MODELS.md \
    FIXED_TEMP_UPDATE_SUMMARY.md \
    REANALYSIS_AND_WHITEPAPER_UPDATE_COMPLETE.md \
    WHITEPAPER_UPDATE_COMPLETE.md \
    WHITEPAPER_UPDATE_STATUS.md \
    STUDY_STATUS_20260323.md \
    CURRENT_STATUS_20260323.md \
    CURRENT_STATUS_MULTILANG.md \
    SESSION_REVIEW.md \
    ROOT_CLEANUP_SUMMARY.md \
    RUST_013_REMOVAL_EXPLANATION.md; do
    [ -f "$file" ] && mv "$file" docs/studies/ && echo "  $file -> docs/studies/"
done

# Codex-specific documentation
for file in \
    CODEX_APP_BENCHMARK_SUMMARY.md \
    CODEX_APP_INSTALLATION.md \
    CODEX_APP_VS_GPT54_COMPARISON.md \
    CODEX_AUTOMATION_GUIDE.md \
    CODEX_BENCHMARK_COMPLETE.md \
    CODEX_BENCHMARK_SUMMARY.md \
    CODEX_FIXES_SUMMARY.md \
    CODEX_QUICK_REFERENCE.md \
    CODEX_SECURITY_SKILL_FINAL_COMPARISON_CORRECTED.md \
    CODEX_SECURITY_SKILL_FINAL_COMPARISON.md \
    CODEX_SECURITY_SKILL_TESTING.md \
    CODEX_SKILL_INSTALLATION.md \
    CODEX_STUDY_FIXES_APPLIED.md; do
    [ -f "$file" ] && mv "$file" docs/ && echo "  $file -> docs/"
done

# Claude Code documentation
for file in \
    CLAUDE_CODE_RUNNING.md \
    CLAUDE_CODE_TEST_INFO.md \
    CLAUDE_CODE_TEST_RESULTS.md; do
    [ -f "$file" ] && mv "$file" docs/ && echo "  $file -> docs/"
done

# Implementation/technical docs
for file in \
    AUTO_BENCHMARK_INTEGRATION.md \
    DETECTOR_IMPLEMENTATION_PLAN.md \
    LANGUAGE_SUPPORT_ANALYSIS.md \
    MULTI_LANGUAGE_DETECTOR_IMPLEMENTATION_COMPLETE.md; do
    [ -f "$file" ] && mv "$file" docs/ && echo "  $file -> docs/"
done

echo ""
echo "=== Moving scripts to scripts/ ==="

# Cleanup scripts
for file in \
    cleanup_all_languages.sh \
    cleanup_root_files.sh \
    delete_rust013.sh \
    organize_files.sh; do
    [ -f "$file" ] && mv "$file" scripts/cleanup/ && echo "  $file -> scripts/cleanup/"
done

# Check/validation scripts
for file in \
    check_completeness.sh \
    check_completion.sh \
    check_missing_files.sh \
    check_validation_progress.sh \
    monitor_reanalysis.sh; do
    [ -f "$file" ] && mv "$file" scripts/ && echo "  $file -> scripts/"
done

# Analysis/utility scripts
for file in \
    regenerate_all_baseline.sh \
    regenerate_temperature_reports.sh \
    reanalyze_all.sh \
    reanalyze_all_simple.sh \
    run_temperature_study.sh \
    run_missing_baseline.sh; do
    [ -f "$file" ] && mv "$file" scripts/ && echo "  $file -> scripts/"
done

# Python utilities (non-core)
for file in \
    check_missing_models.py \
    analyze_temperature_results.py; do
    [ -f "$file" ] && mv "$file" scripts/ && echo "  $file -> scripts/"
done

echo ""
echo "=== Summary ==="
echo "Documentation files in docs/: $(find docs -type f -name "*.md" | wc -l | tr -d ' ')"
echo "Scripts in scripts/: $(find scripts -type f \( -name "*.sh" -o -name "*.py" \) | wc -l | tr -d ' ')"
echo ""
echo "Core files remaining in root:"
ls -1 *.py *.js 2>/dev/null | wc -l | xargs echo "  Code files:"
ls -1 *.md 2>/dev/null | wc -l | xargs echo "  Markdown files:"
