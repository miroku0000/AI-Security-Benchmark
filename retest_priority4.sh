#!/bin/bash
# retest_priority4.sh - Test Priority 4 remaining models

echo "========================================="
echo "Testing: llama3.1"
echo "========================================="
python3 runner.py \
    --code-dir generated_llama3.1 \
    --model llama3.1 \
    --output "reports/llama3.1_208point_$(date +%Y%m%d_%H%M%S).json"

echo ""
echo "========================================="
echo "Testing: claude-sonnet-4-5 (old version)"
echo "========================================="
python3 runner.py \
    --code-dir generated_claude-sonnet-4-5 \
    --model claude-sonnet-4-5-old \
    --output "reports/claude-sonnet-4-5-old_208point_$(date +%Y%m%d_%H%M%S).json"

echo ""
echo "========================================="
echo "Phase 5 Complete: All Priority 4 models tested"
echo "========================================="
