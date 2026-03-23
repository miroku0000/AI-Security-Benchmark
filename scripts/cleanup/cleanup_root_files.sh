#!/bin/bash

# Files that should stay in root (core benchmark tools)
KEEP_FILES=(
    "auto_benchmark.py"
    "code_generator.py"
    "runner.py"
    "cache_manager.py"
    "analyze_temperature_results.py"
    "check_missing_models.py"
    "validate_xml.py"
    "test_multilang_detectors.py"
    "flask_cache_system.py"
    "flask_cache_pickle.py"
    "flask_file_explorer.py"
    "display_comments.js"
)

# Create backup directory
mkdir -p .cleanup_backup

# Count files to clean
total_py=$(ls -1 *.py 2>/dev/null | wc -l | tr -d ' ')
total_js=$(ls -1 *.js 2>/dev/null | wc -l | tr -d ' ')
echo "Found $total_py Python files and $total_js JavaScript files in root"

# Move unwanted files to backup
moved=0
for file in *.py *.js; do
    [ -f "$file" ] || continue
    
    # Check if file should be kept
    keep=false
    for keep_file in "${KEEP_FILES[@]}"; do
        if [ "$file" = "$keep_file" ]; then
            keep=true
            break
        fi
    done
    
    # Move file if it's not in the keep list
    if [ "$keep" = false ]; then
        mv "$file" .cleanup_backup/
        ((moved++))
    fi
done

echo "Moved $moved files to .cleanup_backup/"
echo "Kept ${#KEEP_FILES[@]} core benchmark files in root"
echo ""
echo "To restore: mv .cleanup_backup/* ."
echo "To delete permanently: rm -rf .cleanup_backup/"
