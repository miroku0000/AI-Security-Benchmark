#!/usr/bin/env python3
"""
Temperature 1.0 Variation Study - Generate 4 additional runs for all temperature 1.0 variants only.

Focus on temp=1.0 where variation is highest and most interesting.
- 20 models at temperature 1.0
- 5 runs each (1 existing + 4 new)
- 730 prompts per run
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
TEMPERATURE = 1.0
ADDITIONAL_RUNS = 4
TOTAL_RUNS = 5
VARIATION_BASE_DIR = Path("variation_study")
MAX_API_PARALLEL = 10  # Run 10 API models in parallel
MAX_OLLAMA_PARALLEL = 2  # Run 2 Ollama models in parallel

def find_temp1_variants():
    """Find all model+temperature 1.0 combinations."""
    output_dir = Path("output")
    variants = []

    for temp_dir in output_dir.glob("*_temp1.0"):
        if temp_dir.is_dir():
            # Extract model name
            dir_name = temp_dir.name
            model_name = dir_name.replace('_temp1.0', '')

            # Count files to see if this variant is complete
            file_count = len(list(temp_dir.glob('*')))

            if file_count >= 700:  # Only include complete runs
                variants.append({
                    'model': model_name,
                    'temperature': TEMPERATURE,
                    'original_dir': str(temp_dir),
                    'file_count': file_count
                })

    return sorted(variants, key=lambda x: x['model'])

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
    """Process one model at temperature 1.0 (generate runs 2-5)."""
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

        print(f"    → Generating {variant_id} run{run_num}...")
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
    """Run the temperature 1.0 variation study."""
    print("="*80)
    print("TEMPERATURE 1.0 VARIATION STUDY")
    print("="*80)
    print()

    # Create base directory
    VARIATION_BASE_DIR.mkdir(exist_ok=True)

    # Find variants
    variants = find_temp1_variants()

    # Split by provider
    api_variants = [v for v in variants if detect_provider(v['model']) in ['openai', 'anthropic', 'google']]
    ollama_variants = [v for v in variants if detect_provider(v['model']) == 'ollama']

    print(f"Temperature 1.0 variants: {len(variants)}")
    print(f"  API models: {len(api_variants)} (will run in parallel)")
    print(f"  Ollama models: {len(ollama_variants)} (will run with limited parallelism)")
    print()
    print(f"Strategy:")
    print(f"  - API: {MAX_API_PARALLEL} concurrent generations")
    print(f"  - Ollama: {MAX_OLLAMA_PARALLEL} concurrent (GPU-limited)")
    print(f"  - Resumable: Skips completed runs")
    print()
    print(f"Total new generations: {len(variants)} variants × {ADDITIONAL_RUNS} runs × 730 prompts = {len(variants) * ADDITIONAL_RUNS * 730:,}")
    print()

    start_time = datetime.now()
    all_results = []

    # Run ALL models in parallel - API and Ollama together
    # API models limited to 10, Ollama to 2, but they run simultaneously
    print(f"\n{'='*80}")
    print(f"GENERATING ALL MODELS IN PARALLEL")
    print(f"{'='*80}\n")

    # Create two executor pools running simultaneously
    api_executor = ThreadPoolExecutor(max_workers=MAX_API_PARALLEL)
    ollama_executor = ThreadPoolExecutor(max_workers=MAX_OLLAMA_PARALLEL)

    all_futures = {}

    # Submit API models
    for v in api_variants:
        future = api_executor.submit(process_variant, v)
        all_futures[future] = ('API', v)

    # Submit Ollama models
    for v in ollama_variants:
        future = ollama_executor.submit(process_variant, v)
        all_futures[future] = ('Ollama', v)

    # Process results as they complete
    completed = 0
    total = len(all_futures)

    for future in as_completed(all_futures):
        completed += 1
        provider_type, variant = all_futures[future]

        try:
            result = future.result()
            all_results.append(result)

            if result.get('skipped'):
                print(f"[{completed}/{total}] ({provider_type}) {result['variant_id']}: Already complete ✓")
            else:
                successful = sum(1 for r in result['results'] if r.get('success'))
                print(f"[{completed}/{total}] ({provider_type}) {result['variant_id']}: {successful}/{len(result['results'])} runs generated ✓")

        except Exception as e:
            print(f"[{completed}/{total}] ({provider_type}) {variant['model']}_temp{variant['temperature']}: ERROR - {e}")

    # Shutdown executors
    api_executor.shutdown(wait=True)
    ollama_executor.shutdown(wait=True)

    # Save results
    results_file = VARIATION_BASE_DIR / f"temp1_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
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
