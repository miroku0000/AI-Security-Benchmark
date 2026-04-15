#!/usr/bin/env python3
"""
Analyze security scores across different prompt levels.
Handles files with _levelN suffixes in their names.
"""

import os
import sys
import json
import argparse
from pathlib import Path
from collections import defaultdict

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from runner import SecurityBenchmark


def analyze_level(code_dir, level_name):
    """Run security analysis on a level directory."""
    print(f"\n{'='*70}")
    print(f"Analyzing {level_name}...")
    print(f"{'='*70}")

    benchmark = SecurityBenchmark()
    benchmark.code_dir = code_dir
    benchmark.model_name = level_name

    # Get list of files with _levelN suffix
    files = list(Path(code_dir).glob("*"))
    if not files:
        print(f"WARNING: No files found in {code_dir}")
        return None

    print(f"Found {len(files)} files in {code_dir}")

    # Run analysis
    results = {
        'total': 0,
        'secure': 0,
        'partial': 0,
        'vulnerable': 0,
        'failed': 0,
        'by_category': defaultdict(lambda: {'total': 0, 'secure': 0, 'partial': 0, 'vulnerable': 0})
    }

    # Load prompts to get categories
    import yaml
    prompt_file = "prompts/prompts.yaml"
    if "level" in level_name:
        level_num = level_name.split("level")[1].split("_")[0]
        prompt_file = f"prompts/prompts_level{level_num}_security.yaml"

    try:
        with open(prompt_file, 'r') as f:
            prompt_data = yaml.safe_load(f)
            prompts = prompt_data.get('prompts', [])
    except Exception as e:
        print(f"Warning: Could not load prompts from {prompt_file}: {e}")
        prompts = []

    # Create prompt lookup by ID
    prompt_lookup = {p['id']: p for p in prompts}

    # Analyze each file
    for file_path in files:
        if file_path.is_dir():
            continue

        filename = file_path.name

        # Extract prompt ID from filename (remove _levelN and extension)
        prompt_id = filename
        for ext in ['.py', '.js', '.java', '.go', '.rs', '.cpp', '.cs', '.txt']:
            if prompt_id.endswith(ext):
                prompt_id = prompt_id[:-len(ext)]
                break

        # Remove _levelN suffix
        import re
        prompt_id = re.sub(r'_level\d+$', '', prompt_id)

        results['total'] += 1

        # Get category
        category = 'unknown'
        if prompt_id in prompt_lookup:
            category = prompt_lookup[prompt_id].get('category', 'unknown')

        # Analyze file
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                code = f.read()

            # Run security checks based on category
            is_secure, is_partial, vulnerabilities = benchmark.analyze_code(code, category, str(file_path))

            if is_secure:
                results['secure'] += 1
                results['by_category'][category]['secure'] += 1
            elif is_partial:
                results['partial'] += 1
                results['by_category'][category]['partial'] += 1
            else:
                results['vulnerable'] += 1
                results['by_category'][category]['vulnerable'] += 1

            results['by_category'][category]['total'] += 1

        except Exception as e:
            print(f"Error analyzing {filename}: {e}")
            results['failed'] += 1

    return results


def compare_levels(model, levels=[0, 1, 2, 3, 4, 5]):
    """Compare security scores across multiple levels."""

    all_results = {}

    # Level 0 is the baseline without suffix
    if 0 in levels:
        level0_dir = f"output/{model}"
        if os.path.exists(level0_dir):
            all_results[0] = analyze_level(level0_dir, f"{model}_level0")
        else:
            print(f"WARNING: Level 0 directory not found: {level0_dir}")

    # Levels 1-5 have _levelN suffix
    for level in levels:
        if level == 0:
            continue

        level_dir = f"output/{model}_level{level}"
        if os.path.exists(level_dir):
            all_results[level] = analyze_level(level_dir, f"{model}_level{level}")
        else:
            print(f"WARNING: Level {level} directory not found: {level_dir}")

    # Print comparison
    print(f"\n{'='*70}")
    print(f"COMPARISON: {model}")
    print(f"{'='*70}\n")

    if not all_results:
        print("ERROR: No results to compare")
        return

    # Header
    print(f"{'Level':<10} {'Total':<8} {'Secure':<8} {'Partial':<8} {'Vuln':<8} {'Score %':<10}")
    print("-" * 70)

    # Print each level
    for level in sorted(all_results.keys()):
        r = all_results[level]
        if r and r['total'] > 0:
            secure_pct = (r['secure'] / r['total']) * 100
            print(f"Level {level:<4} {r['total']:<8} {r['secure']:<8} {r['partial']:<8} {r['vulnerable']:<8} {secure_pct:>6.1f}%")

    # Calculate improvements
    if 0 in all_results and all_results[0]:
        baseline = all_results[0]
        baseline_pct = (baseline['secure'] / baseline['total']) * 100

        print(f"\n{'='*70}")
        print("IMPROVEMENTS OVER BASELINE:")
        print(f"{'='*70}\n")

        for level in sorted(all_results.keys()):
            if level == 0:
                continue
            r = all_results[level]
            if r and r['total'] > 0:
                level_pct = (r['secure'] / r['total']) * 100
                improvement = level_pct - baseline_pct
                print(f"Level {level}: {level_pct:.1f}% ({improvement:+.1f}% vs baseline)")

    # Category breakdown for most recent level
    max_level = max(all_results.keys())
    if max_level in all_results and all_results[max_level]:
        print(f"\n{'='*70}")
        print(f"CATEGORY BREAKDOWN (Level {max_level}):")
        print(f"{'='*70}\n")

        r = all_results[max_level]
        print(f"{'Category':<25} {'Total':<8} {'Secure':<8} {'Partial':<8} {'Vuln':<8} {'Score %':<10}")
        print("-" * 70)

        for category in sorted(r['by_category'].keys()):
            cat_data = r['by_category'][category]
            if cat_data['total'] > 0:
                cat_pct = (cat_data['secure'] / cat_data['total']) * 100
                print(f"{category:<25} {cat_data['total']:<8} {cat_data['secure']:<8} "
                      f"{cat_data['partial']:<8} {cat_data['vulnerable']:<8} {cat_pct:>6.1f}%")


def main():
    parser = argparse.ArgumentParser(description='Analyze security across prompt levels')
    parser.add_argument('--model', required=True, help='Model name (e.g., deepseek-coder, gpt-4o-mini)')
    parser.add_argument('--levels', default='0,1,2,3,4,5', help='Comma-separated list of levels to compare')

    args = parser.parse_args()

    levels = [int(l) for l in args.levels.split(',')]

    compare_levels(args.model, levels)


if __name__ == '__main__':
    main()
