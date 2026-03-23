#!/bin/bash

echo "Checking code generation completeness for all models..."
echo "Expected: 66 files per model (Python and JavaScript only)"
echo ""

for dir in output/*/; do
    if [ -d "$dir" ]; then
        model=$(basename "$dir")
        py_count=$(find "$dir" -maxdepth 1 -type f -name "*.py" 2>/dev/null | wc -l | tr -d ' ')
        js_count=$(find "$dir" -maxdepth 1 -type f -name "*.js" 2>/dev/null | wc -l | tr -d ' ')
        total=$((py_count + js_count))

        if [ $total -eq 66 ]; then
            status="✓"
        else
            status="✗ INCOMPLETE"
        fi

        printf "%-40s %3d files  %s\n" "$model" "$total" "$status"
    fi
done | sort

echo ""
echo "Summary:"
complete=$(find output -maxdepth 2 -type f \( -name "*.py" -o -name "*.js" \) | wc -l)
echo "Total files generated: $complete"
