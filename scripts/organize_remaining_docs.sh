#!/bin/bash

echo "=== Moving remaining documentation to docs/ ==="

# Status/summary docs
for file in \
    CURRENT_STATUS.md \
    SESSION_SUMMARY.md \
    ITERATIVE_REFINEMENT_COMPLETE.md; do
    [ -f "$file" ] && mv "$file" docs/studies/ && echo "  $file -> docs/studies/"
done

# Cursor-specific docs
for file in \
    CURSOR_BENCHMARK_STATUS.md \
    CURSOR_FINAL_SUMMARY.md \
    CURSOR_RESULTS_SUMMARY.md \
    CURSOR_SETUP_COMPLETE.md \
    CURSOR_STATUS.md \
    WHITEPAPER_CURSOR_UPDATE.md; do
    [ -f "$file" ] && mv "$file" docs/ && echo "  $file -> docs/"
done

# Temperature study docs
for file in \
    TEMPERATURE_STUDY_FINAL.md \
    TEMPERATURE_STUDY_RESULTS.md \
    WHITEPAPER_TEMPERATURE_UPDATE.md; do
    [ -f "$file" ] && mv "$file" docs/studies/ && echo "  $file -> docs/studies/"
done

# Security prompting research
for file in \
    LEVEL_4_PROMPT_QUALITY_ANALYSIS.md \
    MULTI_LEVEL_SECURITY_PROMPTING_FINDINGS.md \
    SECURITY_PROMPTING_ANSWER.md \
    PROMPT_IMPROVEMENT_SUMMARY.md; do
    [ -f "$file" ] && mv "$file" docs/studies/ && echo "  $file -> docs/studies/"
done

# Implementation status docs
for file in \
    MULTILANGUAGE_IMPLEMENTATION_STATUS.md \
    RETEST_PLAN.md; do
    [ -f "$file" ] && mv "$file" docs/ && echo "  $file -> docs/"
done

# Testing/quick start guides
for file in \
    GPT5_CODEX_TESTING_PLAN.md \
    QUICK_START_CODEX.md \
    INSTALLATION.md; do
    [ -f "$file" ] && mv "$file" docs/ && echo "  $file -> docs/"
done

echo ""
echo "=== Remaining in root ==="
ls -1 *.md 2>/dev/null
