#!/usr/bin/env python3
"""
Find the absolute best model and temperature combination for each language.
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

def find_best_per_language():
    """Find the best model+temperature for each language."""
    prompts_by_lang = load_prompts_by_language()

    # Find all reports
    all_reports = glob.glob("reports/*_20260323.json")

    # Track best for each language
    lang_best = defaultdict(lambda: {'model': None, 'temp': None, 'score': -1, 'percentage': -1})

    for report_path in all_reports:
        try:
            with open(report_path) as f:
                data = json.load(f)

            model_name = data.get('model_name', 'Unknown')

            # Determine temperature
            if '_temp' in model_name:
                base_model = model_name.split('_temp')[0]
                temp = model_name.split('_temp')[1]
                temp_display = f"temp {temp}"
            else:
                base_model = model_name
                temp = 'baseline'
                temp_display = "baseline (0.2)"

            # Analyze by language
            lang_results = analyze_report_by_language(report_path, prompts_by_lang)

            for lang, result in lang_results.items():
                pct = result['percentage']
                if pct > lang_best[lang]['percentage']:
                    lang_best[lang] = {
                        'model': base_model,
                        'temp': temp_display,
                        'score': result['score'],
                        'max_score': result['max_score'],
                        'percentage': pct,
                        'count': result['count']
                    }

        except Exception as e:
            pass

    return lang_best, prompts_by_lang

def print_best_models():
    """Print the best model for each language."""
    lang_best, prompts_by_lang = find_best_per_language()

    print("=" * 120)
    print("BEST MODEL + TEMPERATURE FOR EACH LANGUAGE")
    print("=" * 120)
    print()

    # Sort by language
    lang_order = ['python', 'javascript', 'java', 'csharp', 'cpp', 'go', 'rust']

    for lang in lang_order:
        if lang not in lang_best:
            continue

        best = lang_best[lang]
        num_prompts = len(prompts_by_lang[lang])

        print(f"\n{'=' * 120}")
        print(f"{lang.upper()}")
        print(f"{'=' * 120}")
        print(f"Best Model:        {best['model']}")
        print(f"Best Temperature:  {best['temp']}")
        print(f"Security Score:    {best['score']}/{best['max_score']} ({best['percentage']:.1f}%)")
        print(f"Test Coverage:     {best['count']}/{num_prompts} prompts")

    # Summary table
    print("\n\n" + "=" * 120)
    print("SUMMARY TABLE: Best Model + Temperature Per Language")
    print("=" * 120)
    print()
    print(f"{'Language':<12} | {'Best Model':<30} | {'Temperature':<15} | {'Score':<15} | {'Security %'}")
    print("-" * 120)

    for lang in lang_order:
        if lang not in lang_best:
            continue

        best = lang_best[lang]
        score_str = f"{best['score']}/{best['max_score']}"

        print(f"{lang.capitalize():<12} | {best['model']:<30} | {best['temp']:<15} | {score_str:<15} | {best['percentage']:.1f}%")

    print()
    print("=" * 120)
    print()

    # Additional insights
    print("KEY INSIGHTS:")
    print()

    # Find which model appears most
    model_counts = defaultdict(int)
    for lang, best in lang_best.items():
        model_counts[best['model']] += 1

    print("Most versatile model (appears as best for most languages):")
    for model, count in sorted(model_counts.items(), key=lambda x: x[1], reverse=True)[:3]:
        langs = [lang for lang, best in lang_best.items() if best['model'] == model]
        print(f"  {model}: Best for {count} languages ({', '.join(langs)})")

    print()

    # Temperature distribution
    temp_counts = defaultdict(int)
    for lang, best in lang_best.items():
        temp_counts[best['temp']] += 1

    print("Temperature distribution across best performers:")
    for temp, count in sorted(temp_counts.items(), key=lambda x: x[1], reverse=True):
        langs = [lang for lang, best in lang_best.items() if best['temp'] == temp]
        print(f"  {temp}: {count} languages ({', '.join(langs)})")

    print()

    # Language security ranking
    print("Language security ranking (by best achievable score):")
    lang_scores = [(lang, best['percentage']) for lang, best in lang_best.items()]
    lang_scores.sort(key=lambda x: x[1], reverse=True)

    for i, (lang, pct) in enumerate(lang_scores, 1):
        print(f"  {i}. {lang.capitalize()}: {pct:.1f}%")

    print()
    print("=" * 120)

if __name__ == "__main__":
    print_best_models()
