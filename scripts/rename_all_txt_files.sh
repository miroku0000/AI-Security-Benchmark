#!/bin/bash
# Rename all .txt files to correct extensions across all model directories

set -e

echo "=========================================="
echo "BATCH RENAME: All .txt files -> correct extensions"
echo "=========================================="
echo ""

# Directories to process (those with .txt files)
directories=(
    "output/codex-app-no-skill"
    "output/cursor"
    "output/o3-mini"
    "output/o3"
    "output/o1"
    "output/gpt-5.4-mini"
    "output/gpt-4o-mini"
    "output/gpt-4o"
    "output/gpt-4"
    "output/gpt-3.5-turbo"
    "output/starcoder2"
    "output/qwen2.5-coder_14b"
    "output/qwen2.5-coder"
    "output/mistral"
    "output/llama3.1"
    "output/deepseek-coder_6.7b-instruct"
    "output/deepseek-coder"
    "output/codellama"
    "output/codegemma"
    "output/claude-sonnet-4-5"
    "output/claude-opus-4-6"
    "output/gpt-5.2"
    "output/gpt-5.4"
    "output/codex-app-security-skill"
)

total_dirs=0
total_renamed=0
total_skipped=0
total_errors=0

for dir in "${directories[@]}"; do
    if [ ! -d "$dir" ]; then
        echo "⚠️  Directory not found: $dir - SKIPPED"
        continue
    fi
    
    echo "Processing: $dir"
    
    # Run rename script
    output=$(python3 scripts/rename_txt_files.py --output-dir "$dir" --prompts prompts/prompts.yaml 2>&1)
    
    # Extract summary stats
    renamed=$(echo "$output" | grep "^Renamed:" | awk '{print $2}')
    skipped=$(echo "$output" | grep "^Skipped:" | awk '{print $2}')
    errors=$(echo "$output" | grep "^Errors:" | awk '{print $2}')
    
    echo "  ✅ Renamed: $renamed  ⚠️  Skipped: $skipped  ❌ Errors: $errors"
    echo ""
    
    total_dirs=$((total_dirs + 1))
    total_renamed=$((total_renamed + renamed))
    total_skipped=$((total_skipped + skipped))
    total_errors=$((total_errors + errors))
done

echo "=========================================="
echo "BATCH RENAME COMPLETE"
echo "=========================================="
echo "Directories processed:  $total_dirs"
echo "Total renamed:          $total_renamed"
echo "Total skipped:          $total_skipped"
echo "Total errors:           $total_errors"
echo "=========================================="
