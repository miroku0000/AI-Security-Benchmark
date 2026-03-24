#!/bin/bash

echo "Deleting all rust_013.rs files from output directories..."
echo ""

DELETED_COUNT=0
TOTAL_DIRS=0

# Find all output directories
for dir in output/*/; do
    ((TOTAL_DIRS++))
    rust013_file="${dir}rust_013.rs"
    
    if [ -f "$rust013_file" ]; then
        rm "$rust013_file"
        ((DELETED_COUNT++))
        echo "✓ Deleted: $rust013_file"
    fi
done

echo ""
echo "========================================="
echo "Summary"
echo "========================================="
echo "Directories scanned: $TOTAL_DIRS"
echo "Files deleted: $DELETED_COUNT"
echo ""

# Verify file counts
echo "Verifying file counts after deletion..."
echo ""

for dir in output/*/; do
    dir_name=$(basename "$dir")
    file_count=$(ls "$dir" 2>/dev/null | wc -l | tr -d ' ')
    echo "  ${dir_name}: ${file_count} files"
done
