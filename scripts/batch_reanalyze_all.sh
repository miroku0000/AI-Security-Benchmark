#!/bin/bash
# Batch re-analyze all complete models with improved detectors

set -e

cd "$(dirname "$0")/.."
mkdir -p reports/improved_detectors

# Get all complete models (760 files)
MODELS=($(python3 -c "
import glob
import os

for dir_path in sorted(glob.glob('output/*')):
    if not os.path.isdir(dir_path):
        continue
    file_count = len([f for f in glob.glob(f'{dir_path}/*') if os.path.isfile(f)])
    if file_count >= 760:
        model_name = os.path.basename(dir_path)
        # Skip if already analyzed
        if not os.path.exists(f'reports/improved_detectors/{model_name}_analysis.json'):
            print(model_name)
"))

TOTAL=${#MODELS[@]}
echo "Found $TOTAL models to re-analyze"

# Process in batches
BATCH_SIZE=5
COMPLETED=0

for ((i=0; i<${#MODELS[@]}; i+=BATCH_SIZE)); do
    BATCH=("${MODELS[@]:i:BATCH_SIZE}")

    echo ""
    echo "========================================"
    echo "Batch $((i/BATCH_SIZE + 1)) - Models: ${BATCH[@]}"
    echo "========================================"

    # Start batch in parallel
    for MODEL in "${BATCH[@]}"; do
        echo "Starting: $MODEL"
        python3 runner.py \
            --code-dir "output/$MODEL" \
            --output "reports/improved_detectors/${MODEL}_analysis.json" \
            --model "$MODEL" \
            --temperature 0.0 \
            > "logs/reanalysis_${MODEL}.log" 2>&1 &
    done

    # Wait for batch to complete
    wait

    COMPLETED=$((COMPLETED + ${#BATCH[@]}))
    PERCENT=$((COMPLETED * 100 / TOTAL))

    echo ""
    echo "Progress: $COMPLETED / $TOTAL models ($PERCENT%)"
    echo ""
done

echo ""
echo "========================================"
echo "Re-analysis Complete!"
echo "========================================"
echo "Total models: $TOTAL"
echo "Reports saved to: reports/improved_detectors/"
echo ""
