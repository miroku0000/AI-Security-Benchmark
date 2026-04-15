#!/bin/bash
# Wait for current claude-opus-4-6 to finish, then start remaining Claude models

echo "Waiting for claude-opus-4-6 to complete..."

# Wait for the claude-opus-4-6 process to finish
while ps aux | grep -E "python3 code_generator.py.*claude-opus-4-6" | grep -v grep > /dev/null; do
    sleep 30
done

echo "claude-opus-4-6 completed! Starting remaining Claude models..."
echo ""

# Move generated files to output directory
echo "Moving generated files to output/claude-opus-4-6/..."
mkdir -p output/claude-opus-4-6
mv generated/* output/claude-opus-4-6/ 2>/dev/null || true
echo "Files moved."
echo ""

# Start sequential Claude generation for remaining models
./generate_claude_sequential.sh
