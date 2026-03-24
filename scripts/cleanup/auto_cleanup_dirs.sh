#!/bin/bash

# Legitimate top-level directories
KEEP_DIRS="prompts tests utils analysis docs scripts output reports results static_analyzer_results __pycache__"

for dir in */; do
    dir_name="${dir%/}"
    
    # Skip if it's a keep directory or starts with dot
    if echo "$KEEP_DIRS" | grep -qw "$dir_name" || [[ "$dir_name" == .* ]]; then
        continue
    fi
    
    # Remove test directory
    echo "Removing: $dir_name"
    rm -rf "$dir_name"
done

echo "Cleanup complete!"
