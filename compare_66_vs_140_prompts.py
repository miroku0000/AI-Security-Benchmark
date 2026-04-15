#!/usr/bin/env python3
"""
Compare temperature study results:
- Original 66 prompts (Python + JavaScript only)
- Full 140 prompts (all 7 languages)
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

def analyze_report(report_path, prompt_filter=None):
    """Analyze a report, optionally filtering to specific prompt IDs."""
    with open(report_path) as f:
        data = json.load(f)

    all_results = data.get('detailed_results', [])

    total_score = 0
    max_score = 0
    count = 0

    for result in all_results:
        prompt_id = result.get('prompt_id')

        # Apply filter if provided
        if prompt_filter and prompt_id not in prompt_filter:
            continue

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

def load_all_temperature_data():
    """Load temperature study data for both 66 and 140 prompt sets."""
    original_ids = load_original_prompt_ids()

    # Find all reports
    all_reports = glob.glob("reports/*_20260323.json")

    # Group results by model and temperature
    data_66 = defaultdict(dict)  # [model][temp] = result
    data_140 = defaultdict(dict)

    for report_path in all_reports:
        try:
            # Get results for 66 prompts
            result_66 = analyze_report(report_path, original_ids)
            if result_66['num_prompts'] < 60:
                continue

            # Get results for all 140 prompts
            result_140 = analyze_report(report_path, None)
            if result_140['num_prompts'] < 130:
                continue

            model_name = result_66['model']

            # Determine temperature
            if '_temp' in model_name:
                base_model = model_name.split('_temp')[0]
                temp = model_name.split('_temp')[1]
            else:
                base_model = model_name
                temp = 'baseline'

            data_66[base_model][temp] = result_66
            data_140[base_model][temp] = result_140

        except Exception as e:
            pass

    return data_66, data_140, original_ids

def print_comparison_tables():
    """Print comprehensive comparison tables."""
    data_66, data_140, original_ids = load_all_temperature_data()

    # Get all models that have temperature studies
    models_with_temps = set()
    for model in data_66.keys():
        if len(data_66[model]) > 1:  # Has multiple temperatures
            models_with_temps.add(model)

    print("=" * 140)
    print("TEMPERATURE STUDY COMPARISON: 66 PROMPTS (Python/JS) vs 140 PROMPTS (All Languages)")
    print("=" * 140)
    print()

    # Temperature order
    temp_order = ['0.0', 'baseline', '0.5', '0.7', '1.0']

    # Sort models by best performance on 66 prompts
    model_scores = []
    for model in models_with_temps:
        temps_66 = data_66.get(model, {})
        if temps_66:
            best_pct = max(v['percentage'] for v in temps_66.values())
            model_scores.append((model, best_pct))

    model_scores.sort(key=lambda x: x[1], reverse=True)

    # Print table for each model
    for model, _ in model_scores:
        print(f"\n{'=' * 140}")
        print(f"MODEL: {model}")
        print(f"{'=' * 140}")
        print()

        # Header
        print(f"{'Temperature':<15} | {'66 Prompts (Py/JS)':<25} | {'140 Prompts (All)':<25} | {'Difference':<20}")
        print("-" * 140)

        temps_66 = data_66.get(model, {})
        temps_140 = data_140.get(model, {})

        for temp in temp_order:
            if temp not in temps_66 and temp not in temps_140:
                continue

            temp_display = f"Temp {temp}" if temp != 'baseline' else "Baseline (0.2)"

            # Get data for both
            data_66_temp = temps_66.get(temp, {})
            data_140_temp = temps_140.get(temp, {})

            if data_66_temp and data_140_temp:
                pct_66 = data_66_temp['percentage']
                pct_140 = data_140_temp['percentage']
                score_66 = f"{data_66_temp['score']}/{data_66_temp['max_score']}"
                score_140 = f"{data_140_temp['score']}/{data_140_temp['max_score']}"
                diff = pct_140 - pct_66

                diff_str = f"{diff:+.1f} pp"

                print(f"{temp_display:<15} | {score_66:>8} ({pct_66:5.1f}%)      | {score_140:>8} ({pct_140:5.1f}%)      | {diff_str:<20}")

        # Calculate statistics
        if temps_66 and temps_140:
            print()

            # Variation within each set
            pcts_66 = [v['percentage'] for v in temps_66.values()]
            pcts_140 = [v['percentage'] for v in temps_140.values()]

            var_66 = max(pcts_66) - min(pcts_66)
            var_140 = max(pcts_140) - min(pcts_140)

            # Best temps
            best_temp_66 = max(temps_66.items(), key=lambda x: x[1]['percentage'])
            best_temp_140 = max(temps_140.items(), key=lambda x: x[1]['percentage'])

            print(f"Statistics:")
            print(f"  66 Prompts:  Variation = {var_66:5.1f} pp, Best = {best_temp_66[0]} ({best_temp_66[1]['percentage']:.1f}%)")
            print(f"  140 Prompts: Variation = {var_140:5.1f} pp, Best = {best_temp_140[0]} ({best_temp_140[1]['percentage']:.1f}%)")

    # Summary statistics
    print()
    print("=" * 140)
    print("SUMMARY")
    print("=" * 140)
    print(f"Models analyzed: {len(model_scores)}")
    print(f"Original prompts: {len(original_ids)} (Python + JavaScript)")
    print(f"Total prompts: 140 (Python, JavaScript, Java, C#, C/C++, Go, Rust)")
    print(f"Added languages: 74 prompts (Java: 15, C#: 15, C/C++: 15, Go: 15, Rust: 14)")
    print("=" * 140)

if __name__ == "__main__":
    print_comparison_tables()
