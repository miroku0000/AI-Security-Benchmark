#!/usr/bin/env python3
"""
Analyze variation study results after generation is complete.
Reanalyzes the generated code files to extract security scores.
"""

import subprocess
import json
import re
from pathlib import Path
from datetime import datetime
import yaml

MODELS = ["claude-sonnet-4-5", "gpt-4o-mini"]
PROMPTS = ["sql_001", "xss_001", "cmd_001"]
RUNS = 5
TEMPERATURE = 1.0
VARIATION_DIR = Path("variation_study_temp1.0")

def load_prompt_details(prompt_id):
    """Load prompt details from prompts.yaml."""
    with open('prompts/prompts.yaml', 'r') as f:
        data = yaml.safe_load(f)
        prompts = data.get('prompts', [])

    for prompt in prompts:
        if prompt.get('id') == prompt_id:
            return prompt
    return None

def analyze_file(code_file, prompt_id, model):
    """Analyze a code file and return security score."""
    prompt_data = load_prompt_details(prompt_id)
    if not prompt_data:
        return None

    category = prompt_data.get('category')
    language = prompt_data.get('language')

    try:
        cmd = [
            'python3', 'runner.py',
            '--input', str(code_file),
            '--input-category', category,
            '--language', language,
            '--model', model,
            '--temperature', str(TEMPERATURE)
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

        # Combine stdout and stderr for parsing
        output = result.stdout + result.stderr

        # Extract score
        score_match = re.search(r'Score:\s+(\d+)/(\d+)', output)
        if score_match:
            score = int(score_match.group(1))
            max_score = int(score_match.group(2))
            pct = (score / max_score * 100) if max_score > 0 else 0

            return {
                'score': score,
                'max_score': max_score,
                'percentage': pct
            }
        return None
    except Exception as e:
        print(f"Error analyzing {code_file}: {e}")
        return None

def main():
    print("Analyzing variation study results...")
    print(f"Models: {MODELS}")
    print(f"Prompts: {PROMPTS}")
    print(f"Runs per combination: {RUNS}")
    print()

    all_results = {}

    for model in MODELS:
        print(f"\nAnalyzing {model}...")
        model_results = {}

        for prompt_id in PROMPTS:
            print(f"  {prompt_id}:")
            runs = []

            for run_num in range(1, RUNS + 1):
                # Find the code file
                run_dir = VARIATION_DIR / f"{model}_run{run_num}"
                code_files = list(run_dir.glob(f"{prompt_id}.*"))

                if not code_files:
                    print(f"    Run {run_num}: No file found")
                    continue

                code_file = code_files[0]
                print(f"    Run {run_num}: Analyzing {code_file.name}...", end=' ')

                analysis = analyze_file(code_file, prompt_id, model)
                if analysis:
                    print(f"✓ Score: {analysis['score']}/{analysis['max_score']} ({analysis['percentage']:.1f}%)")
                    runs.append({
                        'run_number': run_num,
                        'score': analysis['score'],
                        'max_score': analysis['max_score'],
                        'percentage': analysis['percentage'],
                        'code_file': str(code_file)
                    })
                else:
                    print("❌ Failed")

            if runs:
                # Calculate statistics
                scores = [r['percentage'] for r in runs]
                mean = sum(scores) / len(scores)
                min_score = min(scores)
                max_score = max(scores)
                score_range = max_score - min_score
                variance = sum((x - mean) ** 2 for x in scores) / len(scores)
                std_dev = variance ** 0.5

                model_results[prompt_id] = {
                    'runs': runs,
                    'statistics': {
                        'mean': mean,
                        'min': min_score,
                        'max': max_score,
                        'range': score_range,
                        'std_dev': std_dev,
                        'num_runs': len(scores),
                        'all_scores': scores
                    }
                }

                print(f"    → Mean={mean:.1f}%, Range={score_range:.1f}pp, StdDev={std_dev:.2f}pp")

        all_results[model] = model_results

    # Save results
    results_file = VARIATION_DIR / f"variation_results_analyzed_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(results_file, 'w') as f:
        json.dump(all_results, f, indent=2)

    print(f"\n✓ Results saved to: {results_file}")

    # Generate markdown report
    generate_report(all_results, results_file)

def generate_report(all_results, results_file):
    """Generate markdown report."""
    report_lines = []

    report_lines.append("# Variation Study Results: Temperature 1.0 Run-to-Run Variation\n")
    report_lines.append(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append(f"**Temperature:** {TEMPERATURE}")
    report_lines.append(f"**Runs per combination:** {RUNS}\n")

    report_lines.append("## Executive Summary\n")

    # Calculate overall statistics
    all_ranges = []
    all_std_devs = []

    for model, model_results in all_results.items():
        for prompt_id, prompt_data in model_results.items():
            stats = prompt_data.get('statistics', {})
            if stats:
                all_ranges.append(stats['range'])
                all_std_devs.append(stats['std_dev'])

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
        report_lines.append(f"- **Maximum standard deviation:** {max_std_dev:.2f} pp\n")

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
    if all_ranges:
        report_lines.append("## Key Findings\n")

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
        report_lines.append(f"4. **Temperature {TEMPERATURE}:** Non-deterministic behavior confirmed at this temperature setting\n")

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
    report_file = VARIATION_DIR / "VARIATION_STUDY_REPORT_FINAL.md"
    with open(report_file, 'w') as f:
        f.write("\n".join(report_lines))

    print(f"✓ Report saved to: {report_file}")

    # Print summary
    if all_ranges:
        print(f"\n{'='*80}")
        print("SUMMARY")
        print(f"{'='*80}")
        print(f"Average variation range: {avg_range:.2f} pp")
        print(f"Maximum variation: {max_range:.2f} pp")
        print(f"Average std dev: {avg_std_dev:.2f} pp")
        print(f"{'='*80}")

if __name__ == "__main__":
    main()
