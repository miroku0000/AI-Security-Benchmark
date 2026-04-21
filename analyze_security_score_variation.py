#!/usr/bin/env python3
"""
Analyze security SCORE variation across 5 runs for all models.
This re-runs the security analysis on all generated files to get actual scores.
"""

import subprocess
import json
import re
import yaml
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import statistics

VARIATION_DIR = Path("variation_study")

def load_prompt_details(prompt_id):
    """Load prompt details from prompts.yaml."""
    with open('prompts/prompts.yaml', 'r') as f:
        data = yaml.safe_load(f)
        prompts = data.get('prompts', [])

    for prompt in prompts:
        if prompt.get('id') == prompt_id:
            return prompt
    return None

def analyze_file(code_file, prompt_id, model, temperature):
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
            '--temperature', str(temperature)
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
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
        return None

def analyze_model_scores(model_dir, sample_size=50):
    """Analyze security score variation for a model across 5 runs."""
    model_name = model_dir.name.replace('_temp1.0', '')
    print(f"\nAnalyzing {model_name}...")

    # Get list of prompts from run1
    run1_dir = model_dir / "run1"
    if not run1_dir.exists():
        return None

    # Get all code files (not JSON)
    all_files = sorted([f.stem for f in run1_dir.iterdir()
                       if f.suffix in ['.py', '.js', '.sol', '.java', '.go', '.php', '.rb']
                       and f.name != 'generation.log'])

    # Sample for efficiency (or use all if small)
    if len(all_files) > sample_size:
        import random
        random.seed(42)  # Reproducible sampling
        sampled_prompts = random.sample(all_files, sample_size)
    else:
        sampled_prompts = all_files

    print(f"  Analyzing {len(sampled_prompts)} prompts across 5 runs...")

    prompt_results = {}
    successful_analyses = 0
    failed_analyses = 0

    for i, prompt_stem in enumerate(sampled_prompts):
        if (i + 1) % 10 == 0:
            print(f"    Progress: {i+1}/{len(sampled_prompts)} prompts...")

        # Get prompt ID and find the file
        prompt_id = prompt_stem

        scores_across_runs = []

        for run_num in [1, 2, 3, 4, 5]:
            run_dir = model_dir / f"run{run_num}"

            # Find the actual file with extension
            matching_files = list(run_dir.glob(f"{prompt_stem}.*"))
            matching_files = [f for f in matching_files if f.suffix != '.json']

            if not matching_files:
                continue

            code_file = matching_files[0]

            analysis = analyze_file(code_file, prompt_id, model_name, 1.0)
            if analysis:
                scores_across_runs.append({
                    'run': run_num,
                    'percentage': analysis['percentage'],
                    'score': analysis['score'],
                    'max_score': analysis['max_score']
                })

        # Calculate statistics if we have scores from multiple runs
        if len(scores_across_runs) >= 3:
            percentages = [s['percentage'] for s in scores_across_runs]

            prompt_results[prompt_id] = {
                'runs': scores_across_runs,
                'statistics': {
                    'mean': statistics.mean(percentages),
                    'median': statistics.median(percentages),
                    'stdev': statistics.stdev(percentages) if len(percentages) > 1 else 0,
                    'min': min(percentages),
                    'max': max(percentages),
                    'range': max(percentages) - min(percentages),
                    'num_runs': len(percentages)
                }
            }
            successful_analyses += 1
        else:
            failed_analyses += 1

    print(f"  ✓ Successfully analyzed: {successful_analyses} prompts")
    if failed_analyses > 0:
        print(f"  ⚠ Failed to analyze: {failed_analyses} prompts")

    return {
        'model': model_name,
        'prompts_analyzed': successful_analyses,
        'prompt_results': prompt_results
    }

def main():
    print("="*80)
    print("SECURITY SCORE VARIATION ANALYSIS")
    print("="*80)
    print("Analyzing actual security scores across 5 runs")
    print("This will take some time as we re-run security analysis...\n")

    # Get all model directories
    model_dirs = sorted([d for d in VARIATION_DIR.iterdir()
                        if d.is_dir() and '_temp1.0' in d.name])

    print(f"Found {len(model_dirs)} models")

    # For initial analysis, let's sample a few models thoroughly
    print("\n⚠ Note: Analyzing a sample of prompts per model for efficiency")
    print("Full analysis would take many hours. Starting with 50 prompts per model...\n")

    all_model_results = []

    for model_dir in model_dirs[:5]:  # Start with first 5 models
        result = analyze_model_scores(model_dir, sample_size=50)
        if result:
            all_model_results.append(result)

    # Calculate aggregate statistics
    print("\n" + "="*80)
    print("AGGREGATE RESULTS")
    print("="*80)

    all_ranges = []
    all_stdevs = []
    all_means = []

    for model_result in all_model_results:
        for prompt_id, prompt_data in model_result['prompt_results'].items():
            stats = prompt_data['statistics']
            all_ranges.append(stats['range'])
            all_stdevs.append(stats['stdev'])
            all_means.append(stats['mean'])

    if all_ranges:
        print(f"\nAcross {len(all_ranges)} prompt analyses:")
        print(f"  Average score range: {statistics.mean(all_ranges):.2f} percentage points")
        print(f"  Maximum score range: {max(all_ranges):.2f} pp")
        print(f"  Minimum score range: {min(all_ranges):.2f} pp")
        print(f"  Average std deviation: {statistics.mean(all_stdevs):.2f} pp")
        print(f"  Maximum std deviation: {max(all_stdevs):.2f} pp")

        # Count how many have significant variation
        significant_variation = sum(1 for r in all_ranges if r > 5.0)
        moderate_variation = sum(1 for r in all_ranges if 1.0 < r <= 5.0)
        minimal_variation = sum(1 for r in all_ranges if r <= 1.0)

        print(f"\n  Variation categories:")
        print(f"    Minimal (≤1pp): {minimal_variation} ({minimal_variation/len(all_ranges)*100:.1f}%)")
        print(f"    Moderate (1-5pp): {moderate_variation} ({moderate_variation/len(all_ranges)*100:.1f}%)")
        print(f"    Significant (>5pp): {significant_variation} ({significant_variation/len(all_ranges)*100:.1f}%)")

    # Save results
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    results_file = VARIATION_DIR / f"security_score_variation_{timestamp}.json"

    output_data = {
        'timestamp': timestamp,
        'models_analyzed': [m['model'] for m in all_model_results],
        'summary': {
            'total_prompts_analyzed': len(all_ranges),
            'avg_range': statistics.mean(all_ranges) if all_ranges else 0,
            'avg_stdev': statistics.mean(all_stdevs) if all_stdevs else 0,
            'max_range': max(all_ranges) if all_ranges else 0,
            'minimal_variation_pct': minimal_variation/len(all_ranges)*100 if all_ranges else 0,
            'moderate_variation_pct': moderate_variation/len(all_ranges)*100 if all_ranges else 0,
            'significant_variation_pct': significant_variation/len(all_ranges)*100 if all_ranges else 0
        },
        'per_model_results': all_model_results
    }

    with open(results_file, 'w') as f:
        json.dump(output_data, f, indent=2)

    print(f"\n✓ Results saved to: {results_file}")
    print("="*80)

    # Generate report
    generate_report(output_data, results_file)

def generate_report(data, results_file):
    """Generate markdown report for security score variation."""
    report_lines = []

    report_lines.append("# Security Score Variation Analysis\n")
    report_lines.append(f"**Analysis Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append(f"**Models Analyzed:** {len(data['models_analyzed'])}")
    report_lines.append(f"**Prompts per Model:** ~50 (sampled)")
    report_lines.append(f"**Total Analyses:** {data['summary']['total_prompts_analyzed']}\n")

    report_lines.append("---\n")

    report_lines.append("## Key Findings\n")

    summary = data['summary']
    report_lines.append(f"- **Average score variation range:** {summary['avg_range']:.2f} percentage points")
    report_lines.append(f"- **Average standard deviation:** {summary['avg_stdev']:.2f} pp")
    report_lines.append(f"- **Maximum variation observed:** {summary['max_range']:.2f} pp\n")

    report_lines.append("### Variation Distribution\n")
    report_lines.append(f"- **Minimal variation (≤1pp):** {summary['minimal_variation_pct']:.1f}%")
    report_lines.append(f"- **Moderate variation (1-5pp):** {summary['moderate_variation_pct']:.1f}%")
    report_lines.append(f"- **Significant variation (>5pp):** {summary['significant_variation_pct']:.1f}%\n")

    report_lines.append("---\n")

    report_lines.append("## Interpretation\n")

    if summary['avg_range'] < 2.0:
        interpretation = "**Low variation** - Security scores are relatively consistent across runs"
    elif summary['avg_range'] < 5.0:
        interpretation = "**Moderate variation** - Some score fluctuation but generally stable"
    else:
        interpretation = "**High variation** - Significant score differences across runs"

    report_lines.append(f"{interpretation}\n")

    report_lines.append("## Comparison: Code vs Score Variation\n")
    report_lines.append("- **Code variation:** 72.4% of code files differ across runs")
    report_lines.append(f"- **Score variation:** {100-summary['minimal_variation_pct']:.1f}% of scores vary by >1pp")
    report_lines.append("- **Insight:** Different code can produce similar security scores\n")

    report_lines.append("---\n")

    report_lines.append("## Models Analyzed\n")
    for model in data['models_analyzed']:
        report_lines.append(f"- {model}")
    report_lines.append("\n")

    report_lines.append("---\n")
    report_lines.append(f"**Full Data:** `{results_file.name}`\n")

    # Write report
    report_file = VARIATION_DIR / "SECURITY_SCORE_VARIATION_REPORT.md"
    with open(report_file, 'w') as f:
        f.write("\n".join(report_lines))

    print(f"✓ Report saved to: {report_file}")

if __name__ == "__main__":
    main()
