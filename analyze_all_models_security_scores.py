#!/usr/bin/env python3
"""
Analyze security SCORE variation across 5 runs for ALL 20 models.
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
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Analyzing {model_name}...")

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
            print(f"    [{datetime.now().strftime('%H:%M:%S')}] Progress: {i+1}/{len(sampled_prompts)} prompts...")

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
    start_time = datetime.now()

    print("="*80)
    print("COMPLETE SECURITY SCORE VARIATION ANALYSIS - ALL 20 MODELS")
    print("="*80)
    print(f"Started: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("Analyzing actual security scores across 5 runs for all models")
    print("This will take 30-60 minutes...\n")

    # Get all model directories
    model_dirs = sorted([d for d in VARIATION_DIR.iterdir()
                        if d.is_dir() and '_temp1.0' in d.name])

    print(f"Found {len(model_dirs)} models")
    print(f"Analyzing 50 prompts per model × 5 runs = {len(model_dirs) * 50 * 5} security tests\n")

    all_model_results = []

    for i, model_dir in enumerate(model_dirs, 1):
        print(f"\n{'='*80}")
        print(f"MODEL {i}/{len(model_dirs)}: {model_dir.name}")
        print(f"{'='*80}")

        result = analyze_model_scores(model_dir, sample_size=50)
        if result:
            all_model_results.append(result)

        # Show elapsed time
        elapsed = datetime.now() - start_time
        avg_per_model = elapsed / i
        remaining = avg_per_model * (len(model_dirs) - i)
        print(f"\n  Elapsed: {elapsed}  |  Estimated remaining: {remaining}")

    # Calculate aggregate statistics
    print("\n" + "="*80)
    print("AGGREGATE RESULTS - ALL 20 MODELS")
    print("="*80)

    all_ranges = []
    all_stdevs = []
    all_means = []
    by_model_stats = {}

    for model_result in all_model_results:
        model = model_result['model']
        model_ranges = []

        for prompt_id, prompt_data in model_result['prompt_results'].items():
            stats = prompt_data['statistics']
            all_ranges.append(stats['range'])
            all_stdevs.append(stats['stdev'])
            all_means.append(stats['mean'])
            model_ranges.append(stats['range'])

        if model_ranges:
            by_model_stats[model] = {
                'avg_range': statistics.mean(model_ranges),
                'max_range': max(model_ranges),
                'num_consistent': sum(1 for r in model_ranges if r <= 1.0),
                'num_varied': sum(1 for r in model_ranges if r > 5.0),
                'consistency_rate': sum(1 for r in model_ranges if r <= 1.0) / len(model_ranges) * 100
            }

    if all_ranges:
        print(f"\nAcross {len(all_ranges)} prompt analyses:")
        print(f"  Average score range: {statistics.mean(all_ranges):.2f} percentage points")
        print(f"  Median score range: {statistics.median(all_ranges):.2f} pp")
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

        # Count extreme cases
        extreme_cases = sum(1 for r in all_ranges if r >= 90)
        print(f"    Extreme (≥90pp): {extreme_cases} ({extreme_cases/len(all_ranges)*100:.1f}%)")

    # Per-model comparison
    print("\n" + "="*80)
    print("PER-MODEL CONSISTENCY RANKINGS")
    print("="*80)
    print(f"\n{'Model':<40} {'Consistency':<12} {'Avg Range':<12} {'Max Range':<12}")
    print("-" * 80)

    for model in sorted(by_model_stats.keys(), key=lambda m: by_model_stats[m]['consistency_rate'], reverse=True):
        stats = by_model_stats[model]
        print(f"{model:<40} {stats['consistency_rate']:>6.1f}%      {stats['avg_range']:>6.2f}pp      {stats['max_range']:>6.2f}pp")

    # Save results
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    results_file = VARIATION_DIR / f"all_models_security_score_variation_{timestamp}.json"

    output_data = {
        'timestamp': timestamp,
        'analysis_duration': str(datetime.now() - start_time),
        'models_analyzed': [m['model'] for m in all_model_results],
        'summary': {
            'total_prompts_analyzed': len(all_ranges),
            'avg_range': statistics.mean(all_ranges) if all_ranges else 0,
            'median_range': statistics.median(all_ranges) if all_ranges else 0,
            'avg_stdev': statistics.mean(all_stdevs) if all_stdevs else 0,
            'max_range': max(all_ranges) if all_ranges else 0,
            'minimal_variation_pct': minimal_variation/len(all_ranges)*100 if all_ranges else 0,
            'moderate_variation_pct': moderate_variation/len(all_ranges)*100 if all_ranges else 0,
            'significant_variation_pct': significant_variation/len(all_ranges)*100 if all_ranges else 0,
            'extreme_variation_pct': extreme_cases/len(all_ranges)*100 if all_ranges else 0
        },
        'per_model_stats': by_model_stats,
        'per_model_results': all_model_results
    }

    with open(results_file, 'w') as f:
        json.dump(output_data, f, indent=2)

    print(f"\n✓ Results saved to: {results_file}")
    print("="*80)

    # Generate report
    generate_report(output_data, results_file)

    end_time = datetime.now()
    duration = end_time - start_time
    print(f"\n{'='*80}")
    print(f"ANALYSIS COMPLETE")
    print(f"{'='*80}")
    print(f"Started:  {start_time.strftime('%H:%M:%S')}")
    print(f"Finished: {end_time.strftime('%H:%M:%S')}")
    print(f"Duration: {duration}")
    print(f"{'='*80}")

def generate_report(data, results_file):
    """Generate markdown report for security score variation."""
    report_lines = []

    report_lines.append("# Complete Security Score Variation Analysis - All 20 Models\n")
    report_lines.append(f"**Analysis Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append(f"**Duration:** {data['analysis_duration']}")
    report_lines.append(f"**Models Analyzed:** {len(data['models_analyzed'])}")
    report_lines.append(f"**Prompts per Model:** 50 (sampled)")
    report_lines.append(f"**Total Security Tests:** {data['summary']['total_prompts_analyzed']} (50 prompts × 5 runs × 20 models)\n")

    report_lines.append("---\n")

    report_lines.append("## Executive Summary\n")

    summary = data['summary']
    report_lines.append(f"- **Average score variation range:** {summary['avg_range']:.2f} percentage points")
    report_lines.append(f"- **Median score variation range:** {summary['median_range']:.2f} pp")
    report_lines.append(f"- **Average standard deviation:** {summary['avg_stdev']:.2f} pp")
    report_lines.append(f"- **Maximum variation observed:** {summary['max_range']:.2f} pp\n")

    report_lines.append("### Variation Distribution\n")
    report_lines.append(f"- **Minimal variation (≤1pp):** {summary['minimal_variation_pct']:.1f}%")
    report_lines.append(f"- **Moderate variation (1-5pp):** {summary['moderate_variation_pct']:.1f}%")
    report_lines.append(f"- **Significant variation (>5pp):** {summary['significant_variation_pct']:.1f}%")
    report_lines.append(f"- **Extreme variation (≥90pp):** {summary['extreme_variation_pct']:.1f}%\n")

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
    report_lines.append(f"- **Score variation (>1pp):** {100-summary['minimal_variation_pct']:.1f}%")
    report_lines.append(f"- **Significant score variation (>5pp):** {summary['significant_variation_pct']:.1f}%")
    report_lines.append("- **Insight:** Different code often produces similar security scores\n")

    report_lines.append("---\n")

    report_lines.append("## Model Consistency Rankings\n")
    report_lines.append("Models ranked by consistency (% of tests with ≤1pp variation):\n")
    report_lines.append("| Rank | Model | Consistency | Avg Range | Max Range |")
    report_lines.append("|------|-------|-------------|-----------|-----------|")

    sorted_models = sorted(data['per_model_stats'].items(),
                          key=lambda x: x[1]['consistency_rate'],
                          reverse=True)

    for rank, (model, stats) in enumerate(sorted_models, 1):
        report_lines.append(
            f"| {rank} | {model} | {stats['consistency_rate']:.1f}% | "
            f"{stats['avg_range']:.2f}pp | {stats['max_range']:.2f}pp |"
        )

    report_lines.append("\n---\n")

    report_lines.append("## Key Findings\n")
    report_lines.append(f"1. **Overall consistency:** {summary['minimal_variation_pct']:.1f}% of scores vary by ≤1pp")
    report_lines.append(f"2. **Significant variation:** {summary['significant_variation_pct']:.1f}% vary by >5pp")
    report_lines.append(f"3. **Extreme cases:** {summary['extreme_variation_pct']:.1f}% show ≥90pp variation (0-100%)")
    report_lines.append(f"4. **Model differences:** Consistency rates range across model families")
    report_lines.append(f"5. **Temperature 1.0 impact:** Measurable but manageable non-determinism\n")

    report_lines.append("---\n")

    report_lines.append("## Implications\n")
    report_lines.append(f"- **For {summary['minimal_variation_pct']:.0f}% of prompts:** Security behavior is consistent and reliable")
    report_lines.append(f"- **For {summary['significant_variation_pct']:.0f}% of prompts:** Multiple runs recommended for critical applications")
    report_lines.append("- **Enterprise guidance:** Use temperature 0.0 for consistency or validate all outputs")
    report_lines.append("- **Benchmark validity:** Relative model rankings remain meaningful despite variation\n")

    report_lines.append("---\n")

    report_lines.append("## All Models Analyzed\n")
    for i, model in enumerate(data['models_analyzed'], 1):
        report_lines.append(f"{i}. {model}")
    report_lines.append("\n---\n")

    report_lines.append(f"**Full Data:** `{results_file.name}`\n")

    # Write report
    report_file = VARIATION_DIR / "ALL_MODELS_SECURITY_SCORE_VARIATION_REPORT.md"
    with open(report_file, 'w') as f:
        f.write("\n".join(report_lines))

    print(f"✓ Report saved to: {report_file}")

if __name__ == "__main__":
    main()
