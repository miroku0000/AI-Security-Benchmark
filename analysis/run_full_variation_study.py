#!/usr/bin/env python3
"""
Full Variation Study - Test run-to-run variation for all 730 prompts across all temperature variants.

Strategy:
- For each model+temperature combination, we already have 1 run (the original output)
- Generate 4 additional runs for each combination
- Store in variation_study/{model}_temp{temp}_run{1-5}/
- Run 1 = copy from original output
- Runs 2-5 = newly generated

This will allow us to measure how much variation exists across the entire benchmark.
"""

import os
import sys
import json
import yaml
import shutil
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List

# Configuration
ADDITIONAL_RUNS = 4  # Generate 4 more runs (we already have 1)
TOTAL_RUNS = 5  # Total of 5 runs per configuration
VARIATION_BASE_DIR = Path("variation_study")
TEMPERATURES = [0.0, 0.5, 0.7, 1.0]

def find_temperature_variants():
    """Find all model+temperature combinations from output/ directory."""
    output_dir = Path("output")
    variants = []

    for temp_dir in output_dir.glob("*_temp*"):
        if temp_dir.is_dir():
            # Extract model name and temperature
            # Format: {model}_temp{temp}
            dir_name = temp_dir.name
            match = dir_name.rsplit('_temp', 1)
            if len(match) == 2:
                model_name = match[0]
                temp_value = float(match[1])

                # Count files to see if this variant is complete
                file_count = len(list(temp_dir.glob('*')))

                variants.append({
                    'model': model_name,
                    'temperature': temp_value,
                    'original_dir': str(temp_dir),
                    'file_count': file_count
                })

    return sorted(variants, key=lambda x: (x['model'], x['temperature']))

def setup_variation_directories(model, temperature):
    """Set up variation study directories for a model+temperature combination."""
    model_temp_base = VARIATION_BASE_DIR / f"{model}_temp{temperature}"

    # Create run directories
    run_dirs = []
    for run_num in range(1, TOTAL_RUNS + 1):
        run_dir = model_temp_base / f"run{run_num}"
        run_dir.mkdir(parents=True, exist_ok=True)
        run_dirs.append(run_dir)

    return run_dirs

def copy_original_run(original_dir, run1_dir):
    """Copy original output as run 1."""
    print(f"    Copying original run from {original_dir}...")

    original_path = Path(original_dir)

    # Count how many files we need to copy
    files_to_copy = list(original_path.glob('*'))

    if not files_to_copy:
        print(f"      ❌ No files found in original directory")
        return False

    # Copy all files
    copied = 0
    for src_file in files_to_copy:
        if src_file.is_file():
            dst_file = run1_dir / src_file.name
            if not dst_file.exists():
                shutil.copy2(src_file, dst_file)
                copied += 1

    print(f"      ✓ Copied {copied} files")
    return True

def generate_additional_runs(model, temperature, run_dirs):
    """Generate code for runs 2-5."""
    print(f"    Generating {ADDITIONAL_RUNS} additional runs...")

    for run_num in range(2, TOTAL_RUNS + 1):
        run_dir = run_dirs[run_num - 1]

        print(f"      Run {run_num}...")

        # Use code_generator.py to generate all 730 prompts
        cmd = [
            'python3', 'code_generator.py',
            '--model', model,
            '--temperature', str(temperature),
            '--output', str(run_dir),
            '--no-cache',  # Disable cache to get different results
            '--retries', '2'
        ]

        # Run in background and track progress
        log_file = run_dir / "generation.log"
        with open(log_file, 'w') as log:
            result = subprocess.run(
                cmd,
                stdout=log,
                stderr=subprocess.STDOUT,
                timeout=None  # No timeout, can take hours
            )

        if result.returncode == 0:
            file_count = len(list(run_dir.glob('*')))
            print(f"        ✓ Generated {file_count} files")
        else:
            print(f"        ❌ Generation failed (exit code {result.returncode})")
            print(f"        Check log: {log_file}")

def process_variant(variant):
    """Process one model+temperature variant."""
    model = variant['model']
    temperature = variant['temperature']
    original_dir = variant['original_dir']
    file_count = variant['file_count']

    print(f"\n{'='*80}")
    print(f"Processing: {model} @ temp={temperature}")
    print(f"  Original files: {file_count}")
    print(f"{'='*80}")

    # Skip if original doesn't have enough files
    if file_count < 700:  # At least 700 out of 730
        print(f"  ⚠️  Skipping - original has only {file_count} files (need 700+)")
        return

    # Set up directories
    run_dirs = setup_variation_directories(model, temperature)

    # Step 1: Copy original as run 1
    if not copy_original_run(original_dir, run_dirs[0]):
        print(f"  ❌ Failed to copy original run")
        return

    # Step 2: Generate runs 2-5
    generate_additional_runs(model, temperature, run_dirs)

    print(f"  ✓ Complete!")

def main():
    """Run the full variation study."""
    print("="*80)
    print("FULL VARIATION STUDY - ALL 730 PROMPTS")
    print("="*80)
    print()
    print(f"Strategy:")
    print(f"  - Run 1: Copy from original output")
    print(f"  - Runs 2-5: Generate fresh code")
    print(f"  - Total: {TOTAL_RUNS} runs per model+temperature")
    print()

    # Create base directory
    VARIATION_BASE_DIR.mkdir(exist_ok=True)

    # Find all temperature variants
    variants = find_temperature_variants()

    print(f"Found {len(variants)} model+temperature combinations:")
    print()

    # Group by model for display
    by_model = {}
    for v in variants:
        model = v['model']
        if model not in by_model:
            by_model[model] = []
        by_model[model].append(v)

    for model, temps in sorted(by_model.items()):
        print(f"  {model:30s} {len(temps)} temps × {TOTAL_RUNS} runs = {len(temps) * TOTAL_RUNS * 730:,} tests")

    print()
    total_tests = len(variants) * TOTAL_RUNS * 730
    print(f"Total tests to run: {total_tests:,}")
    print()

    # Estimate time
    # Assume ~2 seconds per prompt generation (API models) to ~10 seconds (Ollama)
    # We need to generate ADDITIONAL_RUNS * 730 prompts per variant
    new_generations = len(variants) * ADDITIONAL_RUNS * 730
    print(f"New generations needed: {new_generations:,}")
    print(f"Estimated time (if 5s/prompt avg): {new_generations * 5 / 3600:.1f} hours")
    print()

    # Confirm
    response = input("This will take many hours. Continue? (yes/no): ")
    if response.lower() != 'yes':
        print("Aborted.")
        return

    # Process each variant
    start_time = datetime.now()

    for i, variant in enumerate(variants, 1):
        print(f"\n\n{'#'*80}")
        print(f"# VARIANT {i}/{len(variants)}")
        print(f"{'#'*80}")

        process_variant(variant)

        # Show progress
        elapsed = datetime.now() - start_time
        elapsed_sec = elapsed.total_seconds()

        if i > 0:
            avg_time_per_variant = elapsed_sec / i
            remaining = len(variants) - i
            eta_sec = remaining * avg_time_per_variant
            eta_hours = eta_sec / 3600

            print(f"\n  Progress: {i}/{len(variants)} ({i/len(variants)*100:.1f}%)")
            print(f"  Elapsed: {elapsed_sec/3600:.1f}h")
            print(f"  ETA: {eta_hours:.1f}h")

    total_elapsed = datetime.now() - start_time
    print(f"\n{'='*80}")
    print(f"COMPLETE!")
    print(f"Total time: {total_elapsed}")
    print(f"{'='*80}")

if __name__ == "__main__":
    main()
