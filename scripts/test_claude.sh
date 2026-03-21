#!/bin/bash
# Helper script to test Claude models with MYANTHROPIC_API_KEY
# Usage: ./scripts/test_claude.sh claude-opus-4-6 [additional args]

if [ -z "$MYANTHROPIC_API_KEY" ]; then
    echo "Error: MYANTHROPIC_API_KEY not set"
    exit 1
fi

MODEL=${1:-claude-opus-4-6}
shift  # Remove first argument

echo "Testing model: $MODEL"
echo "Additional args: $@"

# Temporarily set ANTHROPIC_API_KEY for this command only
ANTHROPIC_API_KEY=$MYANTHROPIC_API_KEY python3 auto_benchmark.py --model "$MODEL" "$@"

echo ""
echo "✓ Test complete - ANTHROPIC_API_KEY not persisted (no Claude Code conflicts)"
