#!/usr/bin/env python3
"""
Compare models at their optimal temperature settings for 66 prompts.
Shows which models perform best when temperature is optimally tuned.
"""

import json
import glob
import yaml
from collections import defaultdict

def load_original_prompt_ids():
    """Load the original 66 prompts (Python + JavaScript only)."""
    with open('prompts/prompts.yaml') as f:
        data = yaml.safe_load(f)

    prompts = data['prompts']
    original_prompts = [p for p in prompts if p.get('language') in ['python', 'javascript']]
    return set(p['id'] for p in original_prompts)

def filter_report_to_original_prompts(report_path, original_ids):
    """Filter a report to only include original 66 prompts."""
    with open(report_path) as f:
        data = json.load(f)

    all_results = data.get('detailed_results', [])

    total_score = 0
    max_score = 0
    count = 0

    for result in all_results:
        prompt_id = result.get('prompt_id')
        if prompt_id in original_ids:
            score = result.get('score', 0)
            max_possible = result.get('max_score', 2)
            total_score += score
            max_score += max_possible
            count += 1

    percentage = (total_score / max_score * 100) if max_score > 0 else 0

    return {
        'model': data.get('model_name', 'Unknown'),
        'score': total_score,
        'max_score': max_score,
        'percentage': percentage,
        'num_prompts': count
    }

def compare_optimal_temperatures():
    """Compare models at their optimal temperatures."""
    original_ids = load_original_prompt_ids()

    # Find all temperature variant reports
    temp_reports = glob.glob("reports/*_temp*_208point_20260323.json")

    # Also get baseline reports
    baseline_models = [
        'deepseek-coder', 'starcoder2', 'claude-opus-4-6', 'claude-sonnet-4-5',
        'codegemma', 'codellama', 'gpt-3.5-turbo', 'gpt-4', 'gpt-4o', 'gpt-4o-mini',
        'gpt-5.2', 'gpt-5.4', 'gpt-5.4-mini', 'gemini-2.5-flash', 'llama3.1',
        'mistral', 'qwen2.5-coder', 'qwen2.5-coder_14b', 'deepseek-coder_6.7b-instruct'
    ]

    for model in baseline_models:
        baseline = glob.glob(f"reports/{model}_208point_20260323.json")
        temp_reports.extend(baseline)

    # Group by base model
    models = defaultdict(dict)

    for report_path in temp_reports:
        try:
            result = filter_report_to_original_prompts(report_path, original_ids)

            # Skip if not enough prompts analyzed
            if result['num_prompts'] < 60:
                continue

            model_name = result['model']

            # Determine temperature
            if '_temp' in model_name:
                base_model = model_name.split('_temp')[0]
                temp = model_name.split('_temp')[1]
            else:
                base_model = model_name
                temp = 'baseline'

            models[base_model][temp] = {
                'score': result['score'],
                'max_score': result['max_score'],
                'percentage': result['percentage'],
                'num_prompts': result['num_prompts']
            }

        except Exception as e:
            pass

    # Find optimal temperature for each model
    optimal_results = []

    for base_model, temps in models.items():
        if len(temps) < 2:  # Skip models without temperature study
            continue

        # Find best temperature
        best_temp = None
        best_data = None
        best_pct = -1

        for temp, data in temps.items():
            if data['percentage'] > best_pct:
                best_pct = data['percentage']
                best_temp = temp
                best_data = data

        if best_temp:
            # Also get worst and baseline for comparison
            worst_pct = min(d['percentage'] for d in temps.values())
            baseline_pct = temps.get('baseline', {}).get('percentage', None)

            optimal_results.append({
                'model': base_model,
                'best_temp': best_temp,
                'best_score': best_data['score'],
                'best_max': best_data['max_score'],
                'best_pct': best_data['percentage'],
                'worst_pct': worst_pct,
                'baseline_pct': baseline_pct,
                'improvement': best_pct - worst_pct,
                'all_temps': temps
            })

    # Sort by best performance
    optimal_results.sort(key=lambda x: x['best_pct'], reverse=True)

    return optimal_results, original_ids

def print_optimal_comparison():
    """Print comparison of models at optimal temperatures."""
    optimal_results, original_ids = compare_optimal_temperatures()

    print("=" * 140)
    print("MODELS AT OPTIMAL TEMPERATURE: 66 PROMPTS (Python + JavaScript Only)")
    print("=" * 140)
    print()
    print(f"Test Set: {len(original_ids)} prompts (43 Python + 23 JavaScript)")
    print(f"Models Analyzed: {len(optimal_results)}")
    print()
    print("Ranking models by their BEST achievable score with optimal temperature tuning")
    print()
    print("=" * 140)
    print()

    # Main ranking table
    print(f"{'Rank':<6} {'Model':<30} {'Optimal Temp':<15} {'Score':<15} {'Best %':<10} {'Improvement':<15} {'vs Baseline'}")
    print("-" * 140)

    for i, result in enumerate(optimal_results, 1):
        temp_display = f"temp {result['best_temp']}" if result['best_temp'] != 'baseline' else "baseline (0.2)"
        score_str = f"{result['best_score']}/{result['best_max']}"
        improvement_str = f"+{result['improvement']:.1f} pp"

        # Calculate vs baseline
        if result['baseline_pct'] is not None:
            vs_baseline = result['best_pct'] - result['baseline_pct']
            vs_baseline_str = f"{vs_baseline:+.1f} pp" if abs(vs_baseline) > 0.1 else "   = "
        else:
            vs_baseline_str = "N/A"

        print(f"{i:<6} {result['model']:<30} {temp_display:<15} {score_str:<15} {result['best_pct']:>6.1f}%   {improvement_str:<15} {vs_baseline_str}")

    print()
    print("=" * 140)
    print()

    # Summary statistics
    print("SUMMARY STATISTICS:")
    print()

    # Average optimal score
    avg_optimal = sum(r['best_pct'] for r in optimal_results) / len(optimal_results)
    print(f"Average optimal performance: {avg_optimal:.1f}%")

    # Average improvement from tuning
    avg_improvement = sum(r['improvement'] for r in optimal_results) / len(optimal_results)
    print(f"Average improvement from temperature tuning: {avg_improvement:.1f} pp")

    # Models that benefit most from tuning
    print()
    print("Models that benefit MOST from temperature tuning:")
    sorted_by_improvement = sorted(optimal_results, key=lambda x: x['improvement'], reverse=True)
    for i, result in enumerate(sorted_by_improvement[:5], 1):
        temp_display = f"temp {result['best_temp']}" if result['best_temp'] != 'baseline' else "baseline (0.2)"
        print(f"  {i}. {result['model']:30} Best: {temp_display:15} Improvement: {result['improvement']:>5.1f} pp")

    # Models that benefit least
    print()
    print("Models that benefit LEAST from temperature tuning:")
    for i, result in enumerate(sorted_by_improvement[-5:], 1):
        temp_display = f"temp {result['best_temp']}" if result['best_temp'] != 'baseline' else "baseline (0.2)"
        print(f"  {i}. {result['model']:30} Best: {temp_display:15} Improvement: {result['improvement']:>5.1f} pp")

    # Temperature distribution
    print()
    print("Optimal temperature distribution:")
    temp_counts = defaultdict(int)
    for result in optimal_results:
        temp_counts[result['best_temp']] += 1

    for temp, count in sorted(temp_counts.items(), key=lambda x: x[1], reverse=True):
        temp_display = f"temp {temp}" if temp != 'baseline' else "baseline (0.2)"
        print(f"  {temp_display:15} {count} models")

    # Comparison: Top 5 with vs without optimal tuning
    print()
    print("=" * 140)
    print("TOP 5 MODELS: Optimal Temperature vs Baseline/Default")
    print("=" * 140)
    print()
    print(f"{'Model':<30} {'Optimal Temp':<15} {'Optimal Score':<15} {'Baseline Score':<15} {'Difference'}")
    print("-" * 140)

    for result in optimal_results[:5]:
        temp_display = f"temp {result['best_temp']}" if result['best_temp'] != 'baseline' else "baseline (0.2)"

        baseline_score = "N/A"
        diff_str = "N/A"
        if result['baseline_pct'] is not None:
            baseline_score = f"{result['baseline_pct']:.1f}%"
            diff = result['best_pct'] - result['baseline_pct']
            diff_str = f"{diff:+.1f} pp"

        print(f"{result['model']:<30} {temp_display:<15} {result['best_pct']:>6.1f}%          {baseline_score:<15} {diff_str}")

    print()
    print("=" * 140)

if __name__ == "__main__":
    print_optimal_comparison()
