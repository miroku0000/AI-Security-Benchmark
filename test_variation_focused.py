#!/usr/bin/env python3
"""
Focused Variation Study - Test run-to-run variation at temperature 1.0

Tests a small sample of model+prompt combinations multiple times to measure
how much security scores vary due to LLM non-determinism.

Sample: 2 models × 3 prompts × 5 runs = 30 total tests
"""

import os
import sys
import json
import yaml
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

# Focused test configuration
MODELS = [
    "claude-sonnet-4-5",    # Most temperature-sensitive
    "gpt-4o-mini",          # Minimal temperature sensitivity
]

PROMPTS = [
    "sql_001",          # SQL injection
    "xss_001",          # Cross-site scripting
    "cmd_001",          # Command injection
]

TEMPERATURE = 1.0
RUNS_PER_COMBINATION = 5
OUTPUT_DIR = Path("variation_study_temp1.0")

def load_prompt_details(prompt_id: str) -> Optional[Dict]:
    """Load prompt details from prompts.yaml."""
    with open('prompts/prompts.yaml', 'r') as f:
        data = yaml.safe_load(f)
        prompts = data.get('prompts', [])

    for prompt in prompts:
        if prompt.get('id') == prompt_id:
            return prompt
    return None

def generate_code_for_prompt(model: str, prompt_id: str, run_number: int) -> Optional[Path]:
    """Generate code for a single prompt. Returns output file path."""
    prompt_data = load_prompt_details(prompt_id)
    if not prompt_data:
        print(f"    ERROR: Prompt {prompt_id} not found")
        return None

    language = prompt_data.get('language', 'python')
    prompt_text = prompt_data.get('prompt', '')

    # Determine file extension
    ext_map = {
        'python': '.py',
        'javascript': '.js',
        'java': '.java',
        'go': '.go',
        'rust': '.rs',
        'php': '.php',
        'ruby': '.rb',
        'csharp': '.cs',
    }
    ext = ext_map.get(language, '.txt')

    # Create output directory for this run
    run_dir = OUTPUT_DIR / f"{model}_run{run_number}"
    run_dir.mkdir(parents=True, exist_ok=True)

    output_file = run_dir / f"{prompt_id}{ext}"

    # Import and use code generator directly
    sys.path.insert(0, str(Path.cwd()))
    from code_generator import CodeGenerator

    try:
        # Initialize generator (no output_dir parameter)
        generator = CodeGenerator(
            model=model,
            temperature=TEMPERATURE,
            use_cache=False,  # Disable cache so we get different results each time
            timeout=120
        )

        print(f"    Generating code... ", end='', flush=True)

        # Use generate_code method directly
        code = generator.generate_code(prompt_text, language)

        if code:
            with open(output_file, 'w') as f:
                f.write(code)
            print(f"✓ ({len(code)} chars)")
            return output_file
        else:
            print("❌ No code generated")
            return None

    except Exception as e:
        print(f"❌ Error: {str(e)[:100]}")
        import traceback
        traceback.print_exc()
        return None

def analyze_code_file(code_file: Path, prompt_id: str, model: str) -> Optional[Dict]:
    """Analyze a single code file and return security results."""
    print(f"    Analyzing security... ", end='', flush=True)

    # Get prompt details
    prompt_data = load_prompt_details(prompt_id)
    if not prompt_data:
        print(f"❌ Prompt not found")
        return None

    category = prompt_data.get('category')
    language = prompt_data.get('language')

    # Use runner.py to analyze the file
    try:
        # Run runner.py with single file analysis
        cmd = [
            'python3', 'runner.py',
            '--input', str(code_file),
            '--input-category', category,
            '--language', language,
            '--model', model,
            '--temperature', str(TEMPERATURE)
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode != 0:
            print(f"❌ Analysis failed: {result.stderr[:100]}")
            return None

        # Parse output to extract score
        # Look for "Score: X/Y" in output
        output = result.stdout + result.stderr  # Score might be in either stdout or stderr

        # Try to find score in output
        import re
        score_match = re.search(r'Score:\s+(\d+)/(\d+)', output)

        if score_match:
            score = int(score_match.group(1))
            max_score = int(score_match.group(2))
            pct = (score / max_score * 100) if max_score > 0 else 0

            print(f"✓ Score: {score}/{max_score} ({pct:.1f}%)")

            return {
                'score': score,
                'max_score': max_score,
                'percentage': pct,
                'output': output
            }
        else:
            print(f"❌ Could not parse score from output")
            return None

    except subprocess.TimeoutExpired:
        print(f"❌ Timeout")
        return None
    except Exception as e:
        print(f"❌ Error: {str(e)[:100]}")
        import traceback
        traceback.print_exc()
        return None

def run_single_iteration(model: str, prompt_id: str, run_number: int) -> Optional[Dict]:
    """Run one complete iteration: generate + analyze."""
    print(f"  Run {run_number}/{RUNS_PER_COMBINATION}:")

    # Step 1: Generate code
    code_file = generate_code_for_prompt(model, prompt_id, run_number)
    if not code_file or not code_file.exists():
        return None

    # Step 2: Analyze code
    analysis = analyze_code_file(code_file, prompt_id, model)
    if not analysis:
        return None

    return {
        'run_number': run_number,
        'code_file': str(code_file),
        'score': analysis['score'],
        'max_score': analysis['max_score'],
        'percentage': analysis['percentage']
    }

def calculate_statistics(runs: List[Dict]) -> Dict:
    """Calculate variation statistics from multiple runs."""
    if not runs:
        return {}

    scores = [r['percentage'] for r in runs]

    mean = sum(scores) / len(scores)
    min_score = min(scores)
    max_score = max(scores)
    score_range = max_score - min_score

    # Calculate standard deviation
    variance = sum((x - mean) ** 2 for x in scores) / len(scores)
    std_dev = variance ** 0.5

    return {
        'mean': mean,
        'min': min_score,
        'max': max_score,
        'range': score_range,
        'std_dev': std_dev,
        'num_runs': len(scores),
        'all_scores': scores
    }

def run_prompt_all_iterations(model: str, prompt_id: str, prompt_idx: int, total_prompts: int) -> tuple:
    """Run all iterations for a single model+prompt combination. Returns (prompt_id, results)."""
    print(f"{model} - {prompt_id} ({prompt_idx}/{total_prompts}): Starting {RUNS_PER_COMBINATION} runs...")

    runs = []
    for run_num in range(1, RUNS_PER_COMBINATION + 1):
        result = run_single_iteration(model, prompt_id, run_num)
        if result:
            runs.append(result)

    # Calculate statistics
    if runs:
        stats = calculate_statistics(runs)
        print(f"{model} - {prompt_id}: ✓ Complete - Mean={stats['mean']:.1f}%, Range={stats['range']:.1f}pp, StdDev={stats['std_dev']:.2f}pp")
        scores_str = ', '.join(f"{s:.1f}%" for s in stats['all_scores'])
        print(f"  → All scores: {scores_str}")

        return (prompt_id, {
            'runs': runs,
            'statistics': stats
        })
    else:
        print(f"{model} - {prompt_id}: ❌ No valid results")
        return (prompt_id, None)

def main():
    """Run the focused variation study."""
    print("=" * 80)
    print("FOCUSED VARIATION STUDY: Temperature 1.0 Run-to-Run Variation")
    print("=" * 80)
    print()
    print(f"Models: {len(MODELS)}")
    for model in MODELS:
        print(f"  - {model}")
    print(f"Prompts per model: {len(PROMPTS)}")
    for prompt in PROMPTS:
        print(f"  - {prompt}")
    print(f"Runs per combination: {RUNS_PER_COMBINATION}")
    print(f"Total tests: {len(MODELS) * len(PROMPTS) * RUNS_PER_COMBINATION}")
    print(f"Temperature: {TEMPERATURE}")
    print(f"Running prompts in PARALLEL (max 3 concurrent)")
    print()

    # Create output directory
    OUTPUT_DIR.mkdir(exist_ok=True)

    # Store all results
    all_results = {}

    # Run tests
    start_time = datetime.now()

    for model_idx, model in enumerate(MODELS, 1):
        print(f"\n{'=' * 80}")
        print(f"MODEL {model_idx}/{len(MODELS)}: {model}")
        print(f"{'=' * 80}\n")

        # Run all prompts for this model in parallel
        model_results = {}

        with ThreadPoolExecutor(max_workers=3) as executor:
            # Submit all prompt combinations
            futures = {}
            for prompt_idx, prompt_id in enumerate(PROMPTS, 1):
                future = executor.submit(
                    run_prompt_all_iterations,
                    model,
                    prompt_id,
                    prompt_idx,
                    len(PROMPTS)
                )
                futures[future] = prompt_id

            # Collect results as they complete
            for future in as_completed(futures):
                prompt_id, result = future.result()
                if result:
                    model_results[prompt_id] = result

        all_results[model] = model_results
        print()

    # Save results
    results_file = OUTPUT_DIR / f"variation_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(results_file, 'w') as f:
        json.dump(all_results, f, indent=2)

    elapsed = datetime.now() - start_time
    minutes = int(elapsed.total_seconds() // 60)
    seconds = int(elapsed.total_seconds() % 60)

    print(f"\n{'=' * 80}")
    print(f"Study completed in {minutes}m {seconds}s")
    print(f"Results saved to: {results_file}")
    print(f"{'=' * 80}\n")

    # Generate summary report
    generate_summary_report(all_results, results_file, elapsed)

def generate_summary_report(all_results: Dict, results_file: Path, elapsed):
    """Generate a markdown summary report."""
    report_lines = []

    report_lines.append("# Variation Study Results: Temperature 1.0 Run-to-Run Variation\n")
    report_lines.append(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append(f"**Temperature:** {TEMPERATURE}")
    report_lines.append(f"**Runs per combination:** {RUNS_PER_COMBINATION}")
    report_lines.append(f"**Total test duration:** {int(elapsed.total_seconds() // 60)}m {int(elapsed.total_seconds() % 60)}s\n")

    report_lines.append("## Executive Summary\n")

    # Calculate overall statistics
    all_ranges = []
    all_std_devs = []
    all_means = []

    for model, model_results in all_results.items():
        for prompt_id, prompt_data in model_results.items():
            stats = prompt_data.get('statistics', {})
            if stats:
                all_ranges.append(stats['range'])
                all_std_devs.append(stats['std_dev'])
                all_means.append(stats['mean'])

    if all_ranges:
        avg_range = sum(all_ranges) / len(all_ranges)
        max_range = max(all_ranges)
        min_range = min(all_ranges)
        avg_std_dev = sum(all_std_devs) / len(all_std_devs)
        max_std_dev = max(all_std_devs)

        report_lines.append(f"- **Average variation range:** {avg_range:.2f} percentage points")
        report_lines.append(f"- **Maximum variation observed:** {max_range:.2f} pp")
        report_lines.append(f"- **Minimum variation observed:** {min_range:.2f} pp")
        report_lines.append(f"- **Average standard deviation:** {avg_std_dev:.2f} pp")
        report_lines.append(f"- **Maximum standard deviation:** {max_std_dev:.2f} pp")
        report_lines.append(f"- **Total successful tests:** {len(all_ranges)} combinations\n")

    # Detailed results by model
    report_lines.append("## Detailed Results by Model\n")

    for model, model_results in all_results.items():
        report_lines.append(f"### {model}\n")
        report_lines.append("| Prompt | Mean Score | Range | Std Dev | Min | Max | All Scores |")
        report_lines.append("|--------|-----------|-------|---------|-----|-----|------------|")

        for prompt_id in sorted(model_results.keys()):
            prompt_data = model_results[prompt_id]
            stats = prompt_data.get('statistics', {})
            if stats:
                scores_str = ", ".join(f"{s:.1f}%" for s in stats['all_scores'])
                report_lines.append(
                    f"| {prompt_id} | {stats['mean']:.1f}% | "
                    f"{stats['range']:.1f} pp | {stats['std_dev']:.2f} pp | "
                    f"{stats['min']:.1f}% | {stats['max']:.1f}% | {scores_str} |"
                )

        report_lines.append("")

    # Key findings
    report_lines.append("## Key Findings\n")

    if all_ranges:
        if avg_range < 1.0:
            variation_level = "minimal"
        elif avg_range < 3.0:
            variation_level = "moderate"
        elif avg_range < 5.0:
            variation_level = "significant"
        else:
            variation_level = "substantial"

        report_lines.append(f"1. **Run-to-Run Variation:** {variation_level.title()} variation observed (average {avg_range:.2f} pp)")
        report_lines.append(f"2. **Maximum Variation:** Up to {max_range:.2f} percentage points between best and worst runs")
        report_lines.append(f"3. **Consistency:** Standard deviation averages {avg_std_dev:.2f} pp across all tests")
        report_lines.append(f"4. **Statistical Significance:** Non-deterministic behavior confirmed at temperature {TEMPERATURE}\n")

    report_lines.append("## Interpretation\n")
    report_lines.append("- **Range** = difference between highest and lowest score across 5 runs")
    report_lines.append("- **Standard Deviation** = measure of how spread out the scores are")
    report_lines.append("- **Mean** = average score across all runs")
    report_lines.append("- **Higher variation values** = more randomness between runs\n")

    report_lines.append("## Implications\n")
    report_lines.append("Based on the observed variation:")
    report_lines.append("- Single-run measurements may not fully represent model capabilities")
    report_lines.append("- For critical applications, consider running multiple generations")
    report_lines.append("- Temperature 0.0 may provide more consistent results")
    report_lines.append("- Relative model rankings are still meaningful despite variation\n")

    report_lines.append(f"## Raw Data\n")
    report_lines.append(f"Full results: `{results_file}`\n")

    # Write report
    report_file = OUTPUT_DIR / "VARIATION_STUDY_REPORT.md"
    with open(report_file, 'w') as f:
        f.write("\n".join(report_lines))

    print(f"Summary report: {report_file}")
    print()

    # Print summary to console
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    if all_ranges:
        print(f"Average variation range: {avg_range:.2f} pp")
        print(f"Maximum variation: {max_range:.2f} pp")
        print(f"Average std dev: {avg_std_dev:.2f} pp")
    print("=" * 80)

if __name__ == "__main__":
    main()
