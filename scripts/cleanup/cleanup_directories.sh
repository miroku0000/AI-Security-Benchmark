#!/bin/bash

# Legitimate top-level directories according to README.md
KEEP_DIRS=(
    "prompts"
    "tests" 
    "utils"
    "analysis"
    "docs"
    "scripts"
    "output"
    "reports"
    "results"
    "static_analyzer_results"
    "__pycache__"
    ".git"
    ".cleanup_backup"
)

echo "=== Scanning for test directories to remove ==="
echo ""

# Find all top-level directories
count=0
for dir in */; do
    dir_name="${dir%/}"
    
    # Check if directory should be kept
    keep=false
    for keep_dir in "${KEEP_DIRS[@]}"; do
        if [ "$dir_name" = "$keep_dir" ]; then
            keep=true
            break
        fi
    done
    
    # If not in keep list, it's a test artifact
    if [ "$keep" = false ]; then
        echo "Will remove: $dir_name"
        ((count++))
    fi
done

echo ""
echo "Total test directories to remove: $count"
echo ""
read -p "Proceed with deletion? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    for dir in */; do
        dir_name="${dir%/}"
        keep=false
        for keep_dir in "${KEEP_DIRS[@]}"; do
            if [ "$dir_name" = "$keep_dir" ]; then
                keep=true
                break
            fi
        done
        if [ "$keep" = false ]; then
            rm -rf "$dir_name"
            echo "Deleted: $dir_name"
        fi
    done
    echo ""
    echo "Cleanup complete!"
fi
