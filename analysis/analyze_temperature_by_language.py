#!/usr/bin/env python3
"""
Analyze temperature study results broken down by programming language.
Shows how temperature affects each language independently.
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

def analyze_temperature_by_language():
    """Main analysis function."""
    prompts_by_lang = load_prompts_by_language()

    print("=" * 120)
    print("TEMPERATURE STUDY: LANGUAGE-SPECIFIC ANALYSIS")
    print("=" * 120)
    print()
    print(f"Prompts by language:")
    for lang, prompts in sorted(prompts_by_lang.items(), key=lambda x: len(x[1]), reverse=True):
        print(f"  {lang:12} {len(prompts):3} prompts")
    print()

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
            print(f"Error processing {report_path}: {e}")

    # Filter to models with temperature studies
    models_with_temps = {m for m, temps in model_data.items() if len(temps) > 1}

    # Sort models by total best performance
    model_scores = []
    for model in models_with_temps:
        temps = model_data[model]
        # Calculate total score across all temps
        total_best = 0
        for temp_data in temps.values():
            temp_total = sum(lang['percentage'] * lang['count'] for lang in temp_data.values())
            total_best = max(total_best, temp_total)
        model_scores.append((model, total_best))

    model_scores.sort(key=lambda x: x[1], reverse=True)

    # Temperature order
    temp_order = ['0.0', 'baseline', '0.5', '0.7', '1.0']

    # Language order (by number of prompts)
    lang_order = sorted(prompts_by_lang.keys(), key=lambda x: len(prompts_by_lang[x]), reverse=True)

    # Print results for each model
    for model, _ in model_scores[:10]:  # Top 10 models
        print(f"\n{'=' * 120}")
        print(f"MODEL: {model}")
        print(f"{'=' * 120}\n")

        temps = model_data[model]

        # Print table for each language
        for lang in lang_order:
            # Check if this model has data for this language
            has_data = any(lang in temps[t] for t in temps.keys())
            if not has_data:
                continue

            num_prompts = len(prompts_by_lang[lang])
            print(f"\n{lang.upper()} ({num_prompts} prompts)")
            print("-" * 80)

            scores_for_lang = []
            for temp in temp_order:
                if temp not in temps:
                    continue

                temp_data = temps[temp]
                if lang not in temp_data:
                    continue

                lang_data = temp_data[lang]
                temp_display = f"Temp {temp}" if temp != 'baseline' else "Baseline (0.2)"

                score_str = f"{lang_data['score']}/{lang_data['max_score']}"
                pct = lang_data['percentage']

                print(f"  {temp_display:18} {score_str:>10} ({pct:5.1f}%)")
                scores_for_lang.append(pct)

            # Calculate variation for this language
            if len(scores_for_lang) > 1:
                variation = max(scores_for_lang) - min(scores_for_lang)
                print(f"\n  Variation: {variation:5.1f} percentage points")

        # Overall statistics across all languages
        print(f"\n{'SUMMARY ACROSS ALL LANGUAGES':^80}")
        print("-" * 80)

        for temp in temp_order:
            if temp not in temps:
                continue

            temp_data = temps[temp]

            # Calculate weighted average across languages
            total_score = sum(d['score'] for d in temp_data.values())
            total_max = sum(d['max_score'] for d in temp_data.values())

            if total_max > 0:
                overall_pct = (total_score / total_max * 100)
                temp_display = f"Temp {temp}" if temp != 'baseline' else "Baseline (0.2)"
                print(f"  {temp_display:18} {total_score:3}/{total_max} ({overall_pct:5.1f}%)")

    # Generate summary table showing which languages have highest temperature sensitivity
    print(f"\n\n{'=' * 120}")
    print("LANGUAGE SENSITIVITY SUMMARY")
    print(f"{'=' * 120}\n")
    print("Average temperature variation by language across all models:\n")

    lang_variations = defaultdict(list)

    for model, _ in model_scores[:10]:
        temps = model_data[model]

        for lang in lang_order:
            scores = []
            for temp in temp_order:
                if temp in temps and lang in temps[temp]:
                    scores.append(temps[temp][lang]['percentage'])

            if len(scores) > 1:
                variation = max(scores) - min(scores)
                lang_variations[lang].append(variation)

    print(f"{'Language':<15} {'Avg Variation (pp)':<20} {'Models Analyzed':<20} {'Prompts'}")
    print("-" * 80)

    for lang in lang_order:
        if lang in lang_variations and lang_variations[lang]:
            avg_var = sum(lang_variations[lang]) / len(lang_variations[lang])
            num_models = len(lang_variations[lang])
            num_prompts = len(prompts_by_lang[lang])
            print(f"{lang:<15} {avg_var:>8.1f} pp           {num_models:>3} models          {num_prompts:>3}")

    print()
    print("=" * 120)

if __name__ == "__main__":
    analyze_temperature_by_language()
