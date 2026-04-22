#!/usr/bin/env python3
"""
Generate optimal temperature lookup table for each model-language combination.
Shows which temperature produces the best security score for each pairing.
"""

import json
import glob
import yaml
from collections import defaultdict

def load_prompts_by_language():
    """Load prompts grouped by language."""
    with open('prompts/prompts.yaml') as f:
        data = yaml.safe_load(f)

    prompts_by_lang = defaultdict(list)
    for prompt in data['prompts']:
        lang = prompt.get('language', 'unknown')
        prompts_by_lang[lang].append(prompt['id'])

    return prompts_by_lang

def analyze_report_by_language(report_path, prompts_by_lang):
    """Analyze a report broken down by language."""
    with open(report_path) as f:
        data = json.load(f)

    all_results = data.get('detailed_results', [])

    # Group results by language
    lang_scores = defaultdict(lambda: {'score': 0, 'max_score': 0, 'count': 0})

    for result in all_results:
        prompt_id = result.get('prompt_id')
        score = result.get('score', 0)
        max_possible = result.get('max_score', 2)

        # Find which language this prompt belongs to
        for lang, prompt_ids in prompts_by_lang.items():
            if prompt_id in prompt_ids:
                lang_scores[lang]['score'] += score
                lang_scores[lang]['max_score'] += max_possible
                lang_scores[lang]['count'] += 1
                break

    # Calculate percentages
    results = {}
    for lang, data in lang_scores.items():
        if data['max_score'] > 0:
            pct = (data['score'] / data['max_score'] * 100)
            results[lang] = {
                'score': data['score'],
                'max_score': data['max_score'],
                'count': data['count'],
                'percentage': pct
            }

    return results

def generate_optimal_temperature_table():
    """Generate lookup table of optimal temperatures."""
    prompts_by_lang = load_prompts_by_language()

    # Find all temperature study reports
    all_reports = glob.glob("reports/*_temp*_20260323.json")

    # Also get baseline reports
    baseline_models = [
        'deepseek-coder', 'starcoder2', 'claude-opus-4-6', 'claude-sonnet-4-5',
        'codegemma', 'codellama', 'gpt-3.5-turbo', 'gpt-4', 'gpt-4o', 'gpt-4o-mini',
        'gpt-5.2', 'gpt-5.4', 'gpt-5.4-mini', 'gemini-2.5-flash', 'llama3.1',
        'mistral', 'qwen2.5-coder', 'qwen2.5-coder_14b', 'deepseek-coder_6.7b-instruct'
    ]

    for model in baseline_models:
        baseline = glob.glob(f"reports/{model}_208point_20260323.json")
        all_reports.extend(baseline)

    # Group results by model and temperature
    model_data = defaultdict(lambda: defaultdict(dict))

    for report_path in all_reports:
        try:
            with open(report_path) as f:
                data = json.load(f)

            model_name = data.get('model_name', 'Unknown')

            # Determine temperature
            if '_temp' in model_name:
                base_model = model_name.split('_temp')[0]
                temp = model_name.split('_temp')[1]
            else:
                base_model = model_name
                temp = 'baseline'

            # Analyze by language
            lang_results = analyze_report_by_language(report_path, prompts_by_lang)

            model_data[base_model][temp] = lang_results

        except Exception as e:
            pass

    # Filter to models with temperature studies
    models_with_temps = {m for m, temps in model_data.items() if len(temps) > 1}

    # Sort models alphabetically
    sorted_models = sorted(models_with_temps)

    # Language order
    lang_order = ['python', 'javascript', 'java', 'csharp', 'cpp', 'go', 'rust']

    # Temperature order
    temp_order = ['0.0', 'baseline', '0.5', '0.7', '1.0']

    # Build optimal temperature table
    optimal_temps = {}

    for model in sorted_models:
        optimal_temps[model] = {}
        temps = model_data[model]

        for lang in lang_order:
            best_temp = None
            best_score = -1
            all_scores = []

            for temp in temp_order:
                if temp in temps and lang in temps[temp]:
                    pct = temps[temp][lang]['percentage']
                    all_scores.append((temp, pct))
                    if pct > best_score:
                        best_score = pct
                        best_temp = temp

            if best_temp:
                # Find if there are ties
                tied_temps = [t for t, p in all_scores if abs(p - best_score) < 0.1]

                optimal_temps[model][lang] = {
                    'best_temp': best_temp,
                    'best_score': best_score,
                    'all_temps': all_scores,
                    'tied_temps': tied_temps if len(tied_temps) > 1 else None
                }

    return optimal_temps, model_data, lang_order

def print_optimal_table():
    """Print the optimal temperature lookup table."""
    optimal_temps, model_data, lang_order = generate_optimal_temperature_table()

    print("=" * 140)
    print("OPTIMAL TEMPERATURE LOOKUP TABLE")
    print("Best temperature setting for each model-language combination")
    print("=" * 140)
    print()

    # Print compact table
    print("Model-Language Optimal Temperature Matrix:")
    print()

    # Header
    print(f"{'Model':<30} | {'Python':<12} | {'JavaScript':<12} | {'Java':<12} | {'C#':<12} | {'C++':<12} | {'Go':<12} | {'Rust':<12}")
    print("-" * 140)

    for model in sorted(optimal_temps.keys()):
        row = f"{model:<30} |"
        for lang in lang_order:
            if lang in optimal_temps[model]:
                temp = optimal_temps[model][lang]['best_temp']
                score = optimal_temps[model][lang]['best_score']
                temp_display = temp if temp != 'baseline' else '0.2'
                row += f" {temp_display:>4} ({score:4.1f}%) |"
            else:
                row += f" {'N/A':>12} |"
        print(row)

    print()
    print("=" * 140)
    print()

    # Detailed breakdown by model
    print("DETAILED BREAKDOWN: Temperature Performance by Model and Language")
    print("=" * 140)
    print()

    for model in sorted(optimal_temps.keys()):
        print(f"\n{'=' * 140}")
        print(f"MODEL: {model}")
        print(f"{'=' * 140}\n")

        for lang in lang_order:
            if lang not in optimal_temps[model]:
                continue

            opt = optimal_temps[model][lang]
            print(f"{lang.upper()}:")
            print(f"  Best: temp {opt['best_temp']} ({opt['best_score']:.1f}%)")

            # Show all temperatures
            print(f"  All temperatures tested:")
            for temp, pct in opt['all_temps']:
                marker = " ★" if temp == opt['best_temp'] else ""
                temp_display = f"temp {temp}" if temp != 'baseline' else "baseline (0.2)"
                print(f"    {temp_display:15} {pct:5.1f}%{marker}")

            # Show variation
            if len(opt['all_temps']) > 1:
                scores = [p for _, p in opt['all_temps']]
                variation = max(scores) - min(scores)
                print(f"  Variation: {variation:.1f} pp")

            print()

    # Summary statistics
    print("\n" + "=" * 140)
    print("SUMMARY: Temperature Recommendations by Language")
    print("=" * 140)
    print()

    for lang in lang_order:
        print(f"\n{lang.upper()}:")

        temp_counts = defaultdict(int)
        for model in optimal_temps.keys():
            if lang in optimal_temps[model]:
                temp = optimal_temps[model][lang]['best_temp']
                temp_counts[temp] += 1

        print(f"  Most common optimal temperature:")
        for temp, count in sorted(temp_counts.items(), key=lambda x: x[1], reverse=True):
            temp_display = temp if temp != 'baseline' else 'baseline (0.2)'
            print(f"    {temp_display}: {count} models")

        # Calculate average optimal score
        avg_best = sum(optimal_temps[m][lang]['best_score']
                      for m in optimal_temps.keys()
                      if lang in optimal_temps[m]) / len([m for m in optimal_temps.keys() if lang in optimal_temps[m]])

        print(f"  Average best score across all models: {avg_best:.1f}%")

    print("\n" + "=" * 140)

if __name__ == "__main__":
    print_optimal_table()
