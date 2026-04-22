#!/bin/bash

# Regenerate all reports with fixed detectors
# Runs in parallel batches for speed

set -e

BATCH_SIZE=5  # Number of parallel jobs
TOTAL_COUNT=0
SUCCESS_COUNT=0
FAIL_COUNT=0

mkdir -p reports logs

echo "========================================================================"
echo "FULL REPORT REGENERATION"
echo "========================================================================"
echo "Using fixed command injection detector"
echo "Batch size: ${BATCH_SIZE} parallel jobs"
echo ""

# Function to run a single report
run_report() {
    local DIR=$1
    local MODEL_NAME=$2
    local TEMP=${3:-0.2}

    echo "[$(date '+%H:%M:%S')] Starting: ${MODEL_NAME}"

    if python3 runner.py \
        --code-dir "output/${DIR}" \
        --output "reports/${MODEL_NAME}.json" \
        --model "${MODEL_NAME}" \
        --temperature "${TEMP}" \
        > "logs/${MODEL_NAME}_report.log" 2>&1; then
        echo "[$(date '+%H:%M:%S')] ✅ ${MODEL_NAME}"
        return 0
    else
        echo "[$(date '+%H:%M:%S')] ❌ ${MODEL_NAME} FAILED"
        return 1
    fi
}

export -f run_report

# Phase 1: Base models
echo "========================================================================"
echo "PHASE 1: Base Models (27 models)"
echo "========================================================================"

BASE_MODELS=($(ls -1 output/ | grep -v "temp\|level"))

for i in $(seq 0 $BATCH_SIZE $((${#BASE_MODELS[@]} - 1))); do
    BATCH=()
    for j in $(seq 0 $((BATCH_SIZE - 1))); do
        idx=$((i + j))
        if [ $idx -lt ${#BASE_MODELS[@]} ]; then
            BATCH+=("${BASE_MODELS[$idx]}")
        fi
    done

    echo ""
    echo "Processing batch: ${BATCH[@]}"

    for model in "${BATCH[@]}"; do
        run_report "${model}" "${model}" 0.2 &
    done

    wait
    TOTAL_COUNT=$((TOTAL_COUNT + ${#BATCH[@]}))
    echo "Progress: ${TOTAL_COUNT}/27 base models"
done

echo ""
echo "✅ Phase 1 complete: Base models"

# Phase 2: Temperature variants
echo ""
echo "========================================================================"
echo "PHASE 2: Temperature Variants (80 models)"
echo "========================================================================"

TEMP_MODELS=($(ls -1 output/ | grep "temp"))

for i in $(seq 0 $BATCH_SIZE $((${#TEMP_MODELS[@]} - 1))); do
    BATCH=()
    for j in $(seq 0 $((BATCH_SIZE - 1))); do
        idx=$((i + j))
        if [ $idx -lt ${#TEMP_MODELS[@]} ]; then
            BATCH+=("${TEMP_MODELS[$idx]}")
        fi
    done

    for model in "${BATCH[@]}"; do
        # Extract temperature from directory name
        if [[ $model =~ temp([0-9.]+) ]]; then
            TEMP="${BASH_REMATCH[1]}"
        else
            TEMP="0.2"
        fi
        run_report "${model}" "${model}" "${TEMP}" &
    done

    wait
    TOTAL_COUNT=$((TOTAL_COUNT + ${#BATCH[@]}))
    echo "Progress: $((TOTAL_COUNT - 27))/80 temperature variants"
done

echo ""
echo "✅ Phase 2 complete: Temperature variants"

# Phase 3: Level variants
echo ""
echo "========================================================================"
echo "PHASE 3: Level Variants (45 models)"
echo "========================================================================"

LEVEL_MODELS=($(ls -1 output/ | grep "level"))

for i in $(seq 0 $BATCH_SIZE $((${#LEVEL_MODELS[@]} - 1))); do
    BATCH=()
    for j in $(seq 0 $((BATCH_SIZE - 1))); do
        idx=$((i + j))
        if [ $idx -lt ${#LEVEL_MODELS[@]} ]; then
            BATCH+=("${LEVEL_MODELS[$idx]}")
        fi
    done

    for model in "${BATCH[@]}"; do
        run_report "${model}" "${model}" 0.2 &
    done

    wait
    TOTAL_COUNT=$((TOTAL_COUNT + ${#BATCH[@]}))
    echo "Progress: $((TOTAL_COUNT - 107))/45 level variants"
done

echo ""
echo "✅ Phase 3 complete: Level variants"

# Summary
echo ""
echo "========================================================================"
echo "REGENERATION COMPLETE"
echo "========================================================================"
echo "Total reports generated: $(ls -1 reports/*.json | wc -l)"
echo "Total size: $(du -sh reports | cut -f1)"
echo ""
echo "Next steps:"
echo "1. Run: python3 generate_summary_csv.py"
echo "2. Run: python3 generate_multi_level_heatmap_csv.py"
echo "3. Run: python3 generate_temperature_heatmap_csv.py"
echo ""
