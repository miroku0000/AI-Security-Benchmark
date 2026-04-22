#!/usr/bin/env python3
"""
Generate a clean table showing temperature study results for 66 prompts (Python/JS only).
Models as rows, temperatures as columns.
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

def generate_temperature_table():
    """Generate temperature table for 66 prompts."""
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

    # Filter to models with temperature studies
    models_with_temps = {m: temps for m, temps in models.items() if len(temps) > 1}

    # Sort models by best performance
    model_list = []
    for base_model, temps in models_with_temps.items():
        best_pct = max(v['percentage'] for v in temps.values())
        model_list.append((base_model, best_pct, temps))

    model_list.sort(key=lambda x: x[1], reverse=True)

    return model_list, original_ids

def print_temperature_table():
    """Print temperature table in clean format."""
    model_list, original_ids = generate_temperature_table()

    print("=" * 140)
    print("TEMPERATURE STUDY: 66 PROMPTS (Python + JavaScript Only)")
    print("=" * 140)
    print()
    print(f"Test Set: {len(original_ids)} prompts (43 Python + 23 JavaScript)")
    print(f"Models Analyzed: {len(model_list)}")
    print()
    print("=" * 140)
    print()

    # Temperature order
    temp_order = ['0.0', 'baseline', '0.5', '0.7', '1.0']
    temp_headers = ['Temp 0.0', 'Baseline (0.2)', 'Temp 0.5', 'Temp 0.7', 'Temp 1.0']

    # Print header
    print(f"{'Model':<30} | {temp_headers[0]:<15} | {temp_headers[1]:<15} | {temp_headers[2]:<15} | {temp_headers[3]:<15} | {temp_headers[4]:<15} | {'Variation':<12}")
    print("-" * 140)

    # Print each model
    for base_model, best_pct, temps in model_list:
        row = f"{base_model:<30} |"

        scores = []
        for temp in temp_order:
            if temp in temps:
                data = temps[temp]
                score_str = f"{data['score']}/{data['max_score']}"
                pct = data['percentage']
                cell = f"{score_str:>8} ({pct:5.1f}%)"
                scores.append(pct)
            else:
                cell = f"{'N/A':^15}"

            row += f" {cell:<15}|"

        # Calculate variation
        if len(scores) > 1:
            variation = max(scores) - min(scores)
            row += f" {variation:>5.1f} pp"
        else:
            row += f" {'N/A':>8}"

        print(row)

    print()
    print("=" * 140)
    print()

    # Summary statistics
    print("SUMMARY STATISTICS:")
    print()

    # Average variation
    variations = []
    for base_model, best_pct, temps in model_list:
        scores = [v['percentage'] for v in temps.values()]
        if len(scores) > 1:
            variations.append(max(scores) - min(scores))

    avg_variation = sum(variations) / len(variations) if variations else 0
    print(f"Average temperature variation: {avg_variation:.1f} percentage points")
    print()

    # Models with highest variation
    print("Models with highest temperature sensitivity:")
    model_variations = []
    for base_model, best_pct, temps in model_list:
        scores = [v['percentage'] for v in temps.values()]
        if len(scores) > 1:
            variation = max(scores) - min(scores)
            model_variations.append((base_model, variation))

    model_variations.sort(key=lambda x: x[1], reverse=True)
    for i, (model, var) in enumerate(model_variations[:5], 1):
        print(f"  {i}. {model}: {var:.1f} pp")

    print()

    # Best performing temperature overall
    temp_scores = defaultdict(list)
    for base_model, best_pct, temps in model_list:
        for temp, data in temps.items():
            temp_scores[temp].append(data['percentage'])

    print("Average performance by temperature:")
    for temp in temp_order:
        if temp in temp_scores:
            avg = sum(temp_scores[temp]) / len(temp_scores[temp])
            temp_display = f"Temp {temp}" if temp != 'baseline' else "Baseline (0.2)"
            print(f"  {temp_display:15} {avg:5.1f}%")

    print()
    print("=" * 140)

if __name__ == "__main__":
    print_temperature_table()
