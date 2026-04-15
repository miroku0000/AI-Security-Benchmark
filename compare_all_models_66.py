#!/usr/bin/env python3
"""
Compare ALL models (including apps like Codex.app, Claude Code, Cursor) at their optimal
temperature settings for 66 prompts.
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

def compare_all_models():
    """Compare all models including apps."""
    original_ids = load_original_prompt_ids()

    # Find all reports from 2023-03-23
    all_reports = glob.glob("reports/*_20260323.json")

    # Group models by base model for temperature variants
    models = defaultdict(dict)

    # Also track single-run models (apps, etc)
    single_models = []

    for report_path in all_reports:
        try:
            result = filter_report_to_original_prompts(report_path, original_ids)

            # Skip if not enough prompts analyzed
            if result['num_prompts'] < 60:
                continue

            model_name = result['model']

            # Check if this is a temperature variant
            if '_temp' in model_name:
                base_model = model_name.split('_temp')[0]
                temp = model_name.split('_temp')[1]
                models[base_model][temp] = {
                    'score': result['score'],
                    'max_score': result['max_score'],
                    'percentage': result['percentage'],
                    'num_prompts': result['num_prompts']
                }
            # Check if this is a baseline variant
            elif model_name in ['deepseek-coder', 'starcoder2', 'claude-opus-4-6', 'claude-sonnet-4-5',
                               'codegemma', 'codellama', 'gpt-3.5-turbo', 'gpt-4', 'gpt-4o', 'gpt-4o-mini',
                               'gpt-5.2', 'gpt-5.4', 'gpt-5.4-mini', 'gemini-2.5-flash', 'llama3.1',
                               'mistral', 'qwen2.5-coder', 'qwen2.5-coder_14b', 'deepseek-coder_6.7b-instruct']:
                models[model_name]['baseline'] = {
                    'score': result['score'],
                    'max_score': result['max_score'],
                    'percentage': result['percentage'],
                    'num_prompts': result['num_prompts']
                }
            else:
                # Single-run model (app, wrapper, etc)
                single_models.append({
                    'model': model_name,
                    'score': result['score'],
                    'max_score': result['max_score'],
                    'percentage': result['percentage'],
                    'num_prompts': result['num_prompts'],
                    'temp': 'baseline',
                    'is_app': True
                })

        except Exception as e:
            pass

    # Find optimal temperature for each temperature-variant model
    optimal_results = []

    for base_model, temps in models.items():
        if len(temps) >= 2:
            # Temperature study model - find best
            best_temp = None
            best_data = None
            best_pct = -1

            for temp, data in temps.items():
                if data['percentage'] > best_pct:
                    best_pct = data['percentage']
                    best_temp = temp
                    best_data = data

            if best_temp:
                worst_pct = min(d['percentage'] for d in temps.values())
                baseline_pct = temps.get('baseline', {}).get('percentage', None)

                optimal_results.append({
                    'model': base_model,
                    'score': best_data['score'],
                    'max_score': best_data['max_score'],
                    'percentage': best_data['percentage'],
                    'temp': best_temp,
                    'improvement': best_pct - worst_pct,
                    'baseline_pct': baseline_pct,
                    'is_app': False
                })
        elif len(temps) == 1:
            # Single baseline
            temp = list(temps.keys())[0]
            data = temps[temp]
            optimal_results.append({
                'model': base_model,
                'score': data['score'],
                'max_score': data['max_score'],
                'percentage': data['percentage'],
                'temp': temp,
                'improvement': 0,
                'baseline_pct': data['percentage'],
                'is_app': False
            })

    # Add single-run models
    optimal_results.extend(single_models)

    # Sort by percentage
    optimal_results.sort(key=lambda x: x['percentage'], reverse=True)

    return optimal_results, original_ids

def print_all_models_comparison():
    """Print comparison including apps."""
    optimal_results, original_ids = compare_all_models()

    print("=" * 150)
    print("ALL MODELS (INCLUDING APPS) AT OPTIMAL TEMPERATURE: 66 PROMPTS (Python + JavaScript Only)")
    print("=" * 150)
    print()
    print(f"Test Set: {len(original_ids)} prompts (43 Python + 23 JavaScript)")
    print(f"Models Analyzed: {len(optimal_results)}")
    print()
    print("Ranking ALL models including wrapper apps (Codex.app, Claude Code, Cursor)")
    print()
    print("=" * 150)
    print()

    # Main ranking table
    print(f"{'Rank':<6} {'Model':<35} {'Type':<15} {'Temp':<15} {'Score':<15} {'Security %':<12} {'vs Baseline'}")
    print("-" * 150)

    for i, result in enumerate(optimal_results, 1):
        model_type = "App/Wrapper" if result.get('is_app', False) else "API Model"
        temp_display = f"temp {result['temp']}" if result['temp'] != 'baseline' else "baseline (0.2)"
        score_str = f"{result['score']}/{result['max_score']}"

        # Calculate vs baseline
        if not result.get('is_app', False) and result.get('baseline_pct') is not None:
            vs_baseline = result['percentage'] - result['baseline_pct']
            vs_baseline_str = f"{vs_baseline:+.1f} pp" if abs(vs_baseline) > 0.1 else "   = "
        else:
            vs_baseline_str = "N/A"

        print(f"{i:<6} {result['model']:<35} {model_type:<15} {temp_display:<15} {score_str:<15} {result['percentage']:>6.1f}%       {vs_baseline_str}")

    print()
    print("=" * 150)
    print()

    # Summary statistics
    print("SUMMARY STATISTICS:")
    print()

    # Separate apps from API models
    apps = [r for r in optimal_results if r.get('is_app', False)]
    api_models = [r for r in optimal_results if not r.get('is_app', False)]

    print("TOP 5 OVERALL (Any Type):")
    for i, result in enumerate(optimal_results[:5], 1):
        model_type = "App/Wrapper" if result.get('is_app', False) else "API Model"
        temp_display = f"temp {result['temp']}" if result['temp'] != 'baseline' else "baseline (0.2)"
        print(f"  {i}. {result['model']:35} ({model_type:12}) {temp_display:15} {result['percentage']:>6.1f}%")

    print()
    print("TOP 5 API MODELS (Temperature-Tunable):")
    for i, result in enumerate(api_models[:5], 1):
        temp_display = f"temp {result['temp']}" if result['temp'] != 'baseline' else "baseline (0.2)"
        print(f"  {i}. {result['model']:35} {temp_display:15} {result['percentage']:>6.1f}%")

    print()
    print("APPS/WRAPPERS:")
    for i, result in enumerate(apps, 1):
        print(f"  {i}. {result['model']:35} {result['percentage']:>6.1f}%")

    # Average scores
    if apps:
        avg_app = sum(r['percentage'] for r in apps) / len(apps)
        print(f"\nAverage app/wrapper performance: {avg_app:.1f}%")

    if api_models:
        avg_api = sum(r['percentage'] for r in api_models) / len(api_models)
        print(f"Average API model performance (optimal): {avg_api:.1f}%")

    # Gap analysis
    if apps and api_models:
        best_app = apps[0]['percentage']
        best_api = api_models[0]['percentage']
        gap = best_app - best_api
        print(f"\nGap between best app and best API model: {gap:+.1f} pp")

    print()
    print("=" * 150)

if __name__ == "__main__":
    print_all_models_comparison()
