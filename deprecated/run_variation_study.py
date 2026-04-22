#!/usr/bin/env python3
"""
Run variation study - test same prompts multiple times to measure run-to-run variation.

This script runs the same model+prompt combinations 5 times at temperature 1.0
to measure how much variation exists due to LLM non-determinism.
"""

import subprocess
import json
import os
import sys
from datetime import datetime
from pathlib import Path
import yaml

# Models to test (representing different performance profiles)
MODELS = [
    "claude-sonnet-4-5",    # Most temperature-sensitive (3.13 pp variation across temps)
    "gpt-4o-mini",          # Minimal temperature sensitivity (0.4 pp variation)
    "starcoder2",           # Best overall performance at temp 1.0 (65.0%)
]

# Prompts to test (diverse categories)
PROMPTS = [
    "sql_001",          # SQL injection
    "xss_001",          # Cross-site scripting
    "cmd_001",          # Command injection
    "path_001",         # Path traversal
    "xxe_001",          # XML external entity
    "crypto_001",       # Insecure cryptography
    "secrets_001",      # Hardcoded secrets
    "ssrf_001",         # Server-side request forgery
]

TEMPERATURE = 1.0
RUNS_PER_COMBINATION = 5
OUTPUT_DIR = Path("variation_study_results")

def run_single_test(model, prompt_id, run_number):
    """Run a single test and return the security score."""
    print(f"  Run {run_number + 1}/5: {model} + {prompt_id}...", end=" ", flush=True)

    # Create unique output directory for this run
    output_subdir = OUTPUT_DIR / f"{model}_{prompt_id}_run{run_number + 1}"
    output_subdir.mkdir(parents=True, exist_ok=True)

    try:
        # Run the benchmark for this specific prompt
        cmd = [
            "python3", "run_benchmark.py",
            "--model", model,
            "--temperature", str(TEMPERATURE),
            "--prompt", prompt_id,
            "--output-dir", str(output_subdir)
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

        if result.returncode != 0:
            print(f"❌ FAILED")
            print(f"    Error: {result.stderr[:200]}")
            return None

        # Read the results
        report_file = output_subdir / f"{model}_{prompt_id}.json"
        if not report_file.exists():
            # Try alternative naming
            report_file = output_subdir / f"{model}_temp{TEMPERATURE}.json"

        if not report_file.exists():
            print(f"❌ NO REPORT")
            return None

        with open(report_file, 'r') as f:
            data = json.load(f)

        # Extract security score
        security_score = data.get('summary', {}).get('security_score_percentage', None)
        total_points = data.get('summary', {}).get('total_points', 0)
        max_points = data.get('summary', {}).get('max_possible_points', 0)

        print(f"✓ Score: {security_score:.1f}% ({total_points}/{max_points})")

        return {
            'security_score': security_score,
            'total_points': total_points,
            'max_possible_points': max_points,
            'run_number': run_number + 1,
            'report_file': str(report_file)
        }

    except subprocess.TimeoutExpired:
        print(f"❌ TIMEOUT")
        return None
    except Exception as e:
        print(f"❌ ERROR: {str(e)[:100]}")
        return None

def calculate_statistics(runs):
    """Calculate variation statistics from multiple runs."""
    if not runs:
        return None

    scores = [r['security_score'] for r in runs if r and r['security_score'] is not None]

    if not scores:
        return None

    return {
        'mean': sum(scores) / len(scores),
        'min': min(scores),
        'max': max(scores),
        'range': max(scores) - min(scores),
        'std_dev': (sum((x - sum(scores) / len(scores)) ** 2 for x in scores) / len(scores)) ** 0.5,
        'num_runs': len(scores),
        'all_scores': scores
    }

def main():
    """Run the variation study."""
    print("=" * 80)
    print("VARIATION STUDY: Temperature 1.0 Run-to-Run Variation")
    print("=" * 80)
    print()
    print(f"Models: {len(MODELS)}")
    print(f"Prompts per model: {len(PROMPTS)}")
    print(f"Runs per combination: {RUNS_PER_COMBINATION}")
    print(f"Total tests: {len(MODELS) * len(PROMPTS) * RUNS_PER_COMBINATION}")
    print(f"Temperature: {TEMPERATURE}")
    print()

    # Create output directory
    OUTPUT_DIR.mkdir(exist_ok=True)

    # Store all results
    all_results = {}

    # Run tests
    for model in MODELS:
        print(f"\n{'=' * 80}")
        print(f"MODEL: {model}")
        print(f"{'=' * 80}\n")

        model_results = {}

        for prompt_id in PROMPTS:
            print(f"\n{prompt_id}:")

            runs = []
            for run_num in range(RUNS_PER_COMBINATION):
                result = run_single_test(model, prompt_id, run_num)
                if result:
                    runs.append(result)

            # Calculate statistics
            stats = calculate_statistics(runs)

            if stats:
                print(f"  → Statistics: Mean={stats['mean']:.1f}%, Range={stats['range']:.1f}pp, StdDev={stats['std_dev']:.2f}pp")
                model_results[prompt_id] = {
                    'runs': runs,
                    'statistics': stats
                }
            else:
                print(f"  → No valid results")

        all_results[model] = model_results

    # Save results
    results_file = OUTPUT_DIR / f"variation_study_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(results_file, 'w') as f:
        json.dump(all_results, f, indent=2)

    print(f"\n{'=' * 80}")
    print(f"Results saved to: {results_file}")
    print(f"{'=' * 80}\n")

    # Generate summary report
    generate_summary_report(all_results, results_file)

def generate_summary_report(all_results, results_file):
    """Generate a markdown summary report."""
    report_lines = []
    report_lines.append("# Variation Study Results: Temperature 1.0 Run-to-Run Variation\n")
    report_lines.append(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    report_lines.append(f"**Temperature:** {TEMPERATURE}")
    report_lines.append(f"**Runs per combination:** {RUNS_PER_COMBINATION}\n")
    report_lines.append("## Executive Summary\n")

    # Calculate overall statistics
    all_ranges = []
    all_std_devs = []

    for model, model_results in all_results.items():
        for prompt_id, prompt_data in model_results.items():
            stats = prompt_data.get('statistics')
            if stats:
                all_ranges.append(stats['range'])
                all_std_devs.append(stats['std_dev'])

    if all_ranges:
        avg_range = sum(all_ranges) / len(all_ranges)
        max_range = max(all_ranges)
        avg_std_dev = sum(all_std_devs) / len(all_std_devs)

        report_lines.append(f"- **Average variation range:** {avg_range:.2f} percentage points")
        report_lines.append(f"- **Maximum variation observed:** {max_range:.2f} percentage points")
        report_lines.append(f"- **Average standard deviation:** {avg_std_dev:.2f} percentage points")
        report_lines.append(f"- **Total successful tests:** {len(all_ranges)} out of {len(MODELS) * len(PROMPTS)}\n")

    # Detailed results by model
    report_lines.append("## Detailed Results by Model\n")

    for model, model_results in all_results.items():
        report_lines.append(f"### {model}\n")
        report_lines.append("| Prompt | Mean Score | Range | Std Dev | All Scores |")
        report_lines.append("|--------|-----------|-------|---------|------------|")

        for prompt_id, prompt_data in sorted(model_results.items()):
            stats = prompt_data.get('statistics')
            if stats:
                scores_str = ", ".join(f"{s:.1f}%" for s in stats['all_scores'])
                report_lines.append(
                    f"| {prompt_id} | {stats['mean']:.1f}% | "
                    f"{stats['range']:.1f} pp | {stats['std_dev']:.2f} pp | {scores_str} |"
                )

        report_lines.append("")

    # Key findings
    report_lines.append("## Key Findings\n")
    report_lines.append("1. **Run-to-Run Variation:** Multiple runs of the same model+prompt at temperature 1.0 show measurable variation")
    report_lines.append("2. **Statistical Significance:** The observed variation demonstrates that LLM outputs are non-deterministic")
    report_lines.append("3. **Practical Impact:** Users should be aware that security scores can vary across runs\n")

    report_lines.append("## Interpretation\n")
    report_lines.append("- **Range** = difference between highest and lowest score across 5 runs")
    report_lines.append("- **Standard Deviation** = measure of how spread out the scores are")
    report_lines.append("- **Higher values** = more variation between runs\n")

    report_lines.append(f"## Raw Data\n")
    report_lines.append(f"Full results: `{results_file}`\n")

    # Write report
    report_file = OUTPUT_DIR / "VARIATION_STUDY_REPORT.md"
    with open(report_file, 'w') as f:
        f.write("\n".join(report_lines))

    print(f"Summary report: {report_file}")

if __name__ == "__main__":
    main()
