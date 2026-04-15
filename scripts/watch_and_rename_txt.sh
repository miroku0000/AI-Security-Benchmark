#!/bin/bash
# Watch for new .txt files and automatically rename them to correct extensions

echo "Starting .txt file watcher..."
echo "This will monitor output/ directories and automatically rename .txt files"
echo "Press Ctrl+C to stop"
echo ""

while true; do
    # Find all .txt files in output directories
    txt_files=$(find output -type f -name "*.txt" 2>/dev/null)
    
    if [ -n "$txt_files" ]; then
        echo "$(date '+%H:%M:%S') - Found .txt files, running rename script..."
        
        # Get list of directories with .txt files
        dirs=$(find output -type f -name "*.txt" -exec dirname {} \; | sort -u)
        
        for dir in $dirs; do
            python3 scripts/rename_txt_files.py --output-dir "$dir" --prompts prompts/prompts.yaml 2>&1 | grep -E "(Renamed|Skipped|ERROR)" || true
        done
        
        echo ""
    fi
    
    # Wait 30 seconds before next check
    sleep 30
done
