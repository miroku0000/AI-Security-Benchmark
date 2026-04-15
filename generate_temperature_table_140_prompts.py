#!/usr/bin/env python3
"""
Generate a clean table showing temperature study results for ALL 140 prompts.
Models as rows, temperatures as columns.
"""

import json
import glob
from collections import defaultdict

def generate_temperature_table_140():
    """Generate temperature table for all 140 prompts."""

    # Find all temperature variant reports
    temp_reports = glob.glob("reports/*_temp*_20260323.json")

    # Also get baseline reports
    baseline_models = [
        'deepseek-coder', 'starcoder2', 'claude-opus-4-6', 'claude-sonnet-4-5',
        'codegemma', 'codellama', 'gpt-3.5-turbo', 'gpt-4', 'gpt-4o', 'gpt-4o-mini',
        'gpt-5.2', 'gpt-5.4', 'gpt-5.4-mini', 'gemini-2.5-flash', 'llama3.1',
        'mistral', 'qwen2.5-coder', 'qwen2.5-coder_14b', 'deepseek-coder_6.7b-instruct'
    ]

    for model in baseline_models:
        baseline = glob.glob(f"reports/{model}_*_20260323.json")
        # Exclude temperature variants from baseline
        baseline = [r for r in baseline if '_temp' not in r]
        temp_reports.extend(baseline)

    # Group by base model
    models = defaultdict(dict)

    for report_path in temp_reports:
        try:
            with open(report_path) as f:
                data = json.load(f)

            model_name = data.get('model_name', 'Unknown')
            score = data.get('total_score', 0)
            max_score = data.get('max_possible_score', 350)
            percentage = (score / max_score * 100) if max_score > 0 else 0

            # Determine temperature
            if '_temp' in model_name:
                base_model = model_name.split('_temp')[0]
                temp = model_name.split('_temp')[1]
            else:
                base_model = model_name
                temp = 'baseline'

            models[base_model][temp] = {
                'score': score,
                'max_score': max_score,
                'percentage': percentage
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

    return model_list

def print_temperature_table_140():
    """Print temperature table for all 140 prompts in clean format."""
    model_list = generate_temperature_table_140()

    print("=" * 150)
    print("TEMPERATURE STUDY: ALL 140 PROMPTS (All Languages)")
    print("=" * 150)
    print()
    print(f"Test Set: 140 prompts across 8 languages (Python, JavaScript, Java, C#, C++, Go, Rust)")
    print(f"Models Analyzed: {len(model_list)}")
    print(f"Scoring Scale: 0-350 points maximum")
    print()
    print("=" * 150)
    print()

    # Temperature order
    temp_order = ['0.0', 'baseline', '0.5', '0.7', '1.0']
    temp_headers = ['Temp 0.0', 'Baseline (0.2)', 'Temp 0.5', 'Temp 0.7', 'Temp 1.0']

    # Print header
    print(f"{'Model':<30} | {temp_headers[0]:<18} | {temp_headers[1]:<18} | {temp_headers[2]:<18} | {temp_headers[3]:<18} | {temp_headers[4]:<18} | {'Variation':<12}")
    print("-" * 150)

    # Print each model
    for base_model, best_pct, temps in model_list:
        row = f"{base_model:<30} |"

        scores = []
        for temp in temp_order:
            if temp in temps:
                data = temps[temp]
                score_str = f"{data['score']}/{data['max_score']}"
                pct = data['percentage']
                cell = f"{score_str:>9} ({pct:5.1f}%)"
                scores.append(pct)
            else:
                cell = f"{'N/A':^18}"

            row += f" {cell:<18}|"

        # Calculate variation
        if len(scores) > 1:
            variation = max(scores) - min(scores)
            row += f" {variation:>5.1f} pp"
        else:
            row += f" {'N/A':>8}"

        print(row)

    print()
    print("=" * 150)
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

    # Top 5 models at optimal temperature
    print("TOP 5 MODELS AT OPTIMAL TEMPERATURE (140 prompts):")
    print()
    print(f"{'Rank':<6} {'Model':<30} {'Optimal Temp':<15} {'Score':<18} {'Security %'}")
    print("-" * 90)

    for i, (base_model, best_pct, temps) in enumerate(model_list[:5], 1):
        # Find optimal temperature
        best_temp = None
        best_data = None
        best_score = -1

        for temp, data in temps.items():
            if data['percentage'] > best_score:
                best_score = data['percentage']
                best_temp = temp
                best_data = data

        temp_display = f"temp {best_temp}" if best_temp != 'baseline' else "baseline (0.2)"
        score_str = f"{best_data['score']}/{best_data['max_score']}"

        print(f"{i:<6} {base_model:<30} {temp_display:<15} {score_str:<18} {best_pct:.1f}%")

    print()
    print("=" * 150)

if __name__ == "__main__":
    print_temperature_table_140()
