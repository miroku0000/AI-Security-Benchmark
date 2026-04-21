#!/usr/bin/env python3
"""
Parallel Variation Study - Efficiently generate 4 additional runs for all temperature variants.

Optimizations:
- API models run in parallel (up to 4 concurrent)
- Ollama models run sequentially (share GPU)
- Progress tracking and resumable
- Skips already-completed runs
"""

import os
import sys
import json
import shutil
import subprocess
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

# Configuration
ADDITIONAL_RUNS = 4
TOTAL_RUNS = 5
VARIATION_BASE_DIR = Path("variation_study")
MAX_API_PARALLEL = 10  # Run 10 API models in parallel
MAX_OLLAMA_PARALLEL = 2  # Run 2 Ollama models in parallel (GPU can handle it)

def find_temperature_variants():
    """Find all model+temperature combinations."""
    output_dir = Path("output")
    variants = []

    for temp_dir in output_dir.glob("*_temp*"):
        if temp_dir.is_dir():
            dir_name = temp_dir.name
            match = dir_name.rsplit('_temp', 1)
            if len(match) == 2:
                model_name = match[0]
                temp_value = float(match[1])
                file_count = len(list(temp_dir.glob('*')))

                if file_count >= 700:  # Only include complete runs
                    variants.append({
                        'model': model_name,
                        'temperature': temp_value,
                        'original_dir': str(temp_dir),
                        'file_count': file_count
                    })

    return variants

def detect_provider(model_name):
    """Detect if model is API-based or Ollama."""
    model_lower = model_name.lower()

    if any(x in model_lower for x in ['gpt', 'chatgpt', 'o1', 'o3']):
        return 'openai'
    if 'claude' in model_lower:
        return 'anthropic'
    if 'gemini' in model_lower:
        return 'google'

    return 'ollama'

def copy_original_run(original_dir, run1_dir):
    """Copy original output as run 1."""
    original_path = Path(original_dir)
    files_to_copy = list(original_path.glob('*'))

    if not files_to_copy:
        return False

    run1_dir.mkdir(parents=True, exist_ok=True)

    copied = 0
    for src_file in files_to_copy:
        if src_file.is_file():
            dst_file = run1_dir / src_file.name
            if not dst_file.exists():
                shutil.copy2(src_file, dst_file)
                copied += 1

    return copied > 0

def check_run_complete(run_dir):
    """Check if a run is complete (has 700+ files)."""
    if not run_dir.exists():
        return False
    file_count = len(list(run_dir.glob('*')))
    return file_count >= 700

def generate_single_run(model, temperature, output_dir, run_num):
    """Generate code for one run."""
    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        'python3', 'code_generator.py',
        '--model', model,
        '--temperature', str(temperature),
        '--output', str(output_dir),
        '--no-cache',
        '--retries', '2'
    ]

    log_file = output_dir / "generation.log"
    start_time = time.time()

    with open(log_file, 'w') as log:
        result = subprocess.run(
            cmd,
            stdout=log,
            stderr=subprocess.STDOUT
        )

    elapsed = time.time() - start_time

    if result.returncode == 0:
        file_count = len(list(output_dir.glob('*')))
        return {
            'success': True,
            'file_count': file_count,
            'elapsed': elapsed,
            'log': str(log_file)
        }
    else:
        return {
            'success': False,
            'exit_code': result.returncode,
            'elapsed': elapsed,
            'log': str(log_file)
        }

def process_variant(variant):
    """Process one model+temperature variant (generate runs 2-5)."""
    model = variant['model']
    temperature = variant['temperature']
    original_dir = variant['original_dir']

    variant_id = f"{model}_temp{temperature}"
    model_temp_base = VARIATION_BASE_DIR / variant_id

    # Set up run directories
    run_dirs = []
    for run_num in range(1, TOTAL_RUNS + 1):
        run_dir = model_temp_base / f"run{run_num}"
        run_dirs.append(run_dir)

    # Check if already complete
    all_complete = all(check_run_complete(rd) for rd in run_dirs)
    if all_complete:
        return {
            'variant_id': variant_id,
            'status': 'already_complete',
            'skipped': True
        }

    # Copy run 1 if needed
    if not check_run_complete(run_dirs[0]):
        copy_original_run(original_dir, run_dirs[0])

    # Generate runs 2-5
    results = []
    for run_num in range(2, TOTAL_RUNS + 1):
        run_dir = run_dirs[run_num - 1]

        if check_run_complete(run_dir):
            results.append({
                'run': run_num,
                'status': 'skipped_complete'
            })
            continue

        result = generate_single_run(model, temperature, run_dir, run_num)
        result['run'] = run_num
        results.append(result)

    return {
        'variant_id': variant_id,
        'model': model,
        'temperature': temperature,
        'results': results,
        'skipped': False
    }

def main():
    """Run the parallel variation study."""
    print("="*80)
    print("PARALLEL VARIATION STUDY")
    print("="*80)
    print()

    # Create base directory
    VARIATION_BASE_DIR.mkdir(exist_ok=True)

    # Find variants
    variants = find_temperature_variants()

    # Split by provider
    api_variants = [v for v in variants if detect_provider(v['model']) in ['openai', 'anthropic', 'google']]
    ollama_variants = [v for v in variants if detect_provider(v['model']) == 'ollama']

    print(f"Total variants: {len(variants)}")
    print(f"  API models: {len(api_variants)} (will run in parallel)")
    print(f"  Ollama models: {len(ollama_variants)} (will run sequentially)")
    print()
    print(f"Strategy:")
    print(f"  - API: {MAX_API_PARALLEL} concurrent generations")
    print(f"  - Ollama: Sequential (GPU-bound)")
    print(f"  - Resumable: Skips completed runs")
    print()

    start_time = datetime.now()
    all_results = []

    # Phase 1: API models in parallel
    if api_variants:
        print(f"\n{'='*80}")
        print(f"PHASE 1: API MODELS ({len(api_variants)} variants)")
        print(f"{'='*80}\n")

        with ThreadPoolExecutor(max_workers=MAX_API_PARALLEL) as executor:
            futures = {
                executor.submit(process_variant, v): v
                for v in api_variants
            }

            for i, future in enumerate(as_completed(futures), 1):
                variant = futures[future]
                try:
                    result = future.result()
                    all_results.append(result)

                    if result.get('skipped'):
                        print(f"[{i}/{len(api_variants)}] {result['variant_id']}: Already complete ✓")
                    else:
                        print(f"[{i}/{len(api_variants)}] {result['variant_id']}: Generated {len(result['results'])} runs")

                except Exception as e:
                    print(f"[{i}/{len(api_variants)}] {variant['model']}_temp{variant['temperature']}: ERROR - {e}")

    # Phase 2: Ollama models in parallel (limited)
    if ollama_variants:
        print(f"\n{'='*80}")
        print(f"PHASE 2: OLLAMA MODELS ({len(ollama_variants)} variants)")
        print(f"{'='*80}\n")

        with ThreadPoolExecutor(max_workers=MAX_OLLAMA_PARALLEL) as executor:
            futures = {
                executor.submit(process_variant, v): v
                for v in ollama_variants
            }

            for i, future in enumerate(as_completed(futures), 1):
                variant = futures[future]
                try:
                    result = future.result()
                    all_results.append(result)

                    if result.get('skipped'):
                        print(f"[{i}/{len(ollama_variants)}] {result['variant_id']}: Already complete ✓")
                    else:
                        print(f"[{i}/{len(ollama_variants)}] {result['variant_id']}: Generated {len(result['results'])} runs")

                except Exception as e:
                    print(f"[{i}/{len(ollama_variants)}] {variant['model']}_temp{variant['temperature']}: ERROR - {e}")

    # Save results
    results_file = VARIATION_BASE_DIR / f"generation_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(results_file, 'w') as f:
        json.dump(all_results, f, indent=2)

    elapsed = datetime.now() - start_time
    print(f"\n{'='*80}")
    print(f"COMPLETE!")
    print(f"Total time: {elapsed}")
    print(f"Results: {results_file}")
    print(f"{'='*80}")

if __name__ == "__main__":
    main()
