#!/bin/bash

for temp in 0.0 0.5 0.7 1.0; do
    echo "Completing claude-sonnet-4-5 at temperature $temp..."
    python3 code_generator.py --model claude-sonnet-4-5 --temperature $temp --output output/claude-sonnet-4-5_temp$temp --retries 3
    
    file_count=$(ls output/claude-sonnet-4-5_temp$temp/ 2>/dev/null | wc -l | tr -d ' ')
    if [ "$file_count" -eq 141 ]; then
        echo "✓ Completed claude-sonnet-4-5 temp $temp (141/141 files)"
    else
        echo "⚠ claude-sonnet-4-5 temp $temp incomplete: $file_count/141 files"
    fi
done

echo "Claude Sonnet retry complete!"
