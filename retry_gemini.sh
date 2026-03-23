#!/bin/bash
export GEMINI_API_KEY=AIzaSyD78DKc5-VB4TdiEJ6fZpzolz1QSWPTKJY

for temp in 0.0 0.5 0.7 1.0; do
    echo "Generating gemini-2.5-flash at temperature $temp..."
    python3 code_generator.py --model gemini-2.5-flash --temperature $temp --output output/gemini-2.5-flash_temp$temp --retries 3
    
    file_count=$(ls output/gemini-2.5-flash_temp$temp/ 2>/dev/null | wc -l | tr -d ' ')
    if [ "$file_count" -eq 141 ]; then
        echo "✓ Completed gemini-2.5-flash temp $temp (141/141 files)"
    else
        echo "⚠ gemini-2.5-flash temp $temp incomplete: $file_count/141 files"
    fi
done

echo "Gemini retry complete!"
