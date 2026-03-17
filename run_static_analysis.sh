#!/bin/bash

set -e  # exit on error
set -v

RESULTS_DIR="static_analyzer_results"

# Clean and recreate results directory
rm -rf "$RESULTS_DIR"
mkdir -p "$RESULTS_DIR"

shopt -s nullglob
for dir in generated_*/; do
    # Extract model name from directory (e.g., generated_gpt-4o -> gpt-4o)
    dirname=$(basename "${dir%/}")
    model_name="${dirname#generated_}"

    src_dir="$(realpath "$dir")"

    target_dir="$RESULTS_DIR/$model_name"
    mkdir -p "$target_dir"
    target_dir=$(realpath "$target_dir")

    echo "Running analyzers: $src_dir -> $target_dir"

    # -e DEBUG="1" \

    podman run --rm \
        -e SRCDIR="$src_dir" \
        --mount type=bind,source="$src_dir",target=/src \
        --mount type=bind,source="$target_dir",target=/output \
        localhost/ioa
done
shopt -u nullglob

echo ""
echo "Static analysis complete! Results stored in: $RESULTS_DIR/"
