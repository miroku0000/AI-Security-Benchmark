#!/usr/bin/env python3
"""
Re-analyze temperature study results using only the original 66 prompts.
(Python and JavaScript only - the original benchmark before multi-language expansion)
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

    # Get detailed results (list format)
    all_results = data.get('detailed_results', [])

    # Filter to only original prompts
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

def analyze_temperature_study():
    """Analyze temperature study with only original 66 prompts."""
    original_ids = load_original_prompt_ids()
    print(f"Loaded {len(original_ids)} original prompt IDs (Python + JavaScript)")
    print()

    # Find all temperature variant reports (350-point scale)
    temp_reports = glob.glob("reports/*_temp*_208point_20260323.json")
    baseline_reports = []

    # Also get baseline reports (no temperature suffix)
    for model in ['deepseek-coder', 'starcoder2', 'claude-opus-4-6', 'claude-sonnet-4-5',
                  'codegemma', 'codellama', 'gpt-3.5-turbo', 'gpt-4', 'gpt-4o', 'gpt-4o-mini',
                  'gpt-5.2', 'gpt-5.4', 'gpt-5.4-mini', 'gemini-2.5-flash', 'llama3.1',
                  'mistral', 'qwen2.5-coder', 'qwen2.5-coder_14b', 'deepseek-coder_6.7b-instruct']:
        report = f"reports/{model}_208point_20260323.json"
        if glob.glob(report):
            baseline_reports.append(report)

    all_reports = temp_reports + baseline_reports

    # Group by base model
    models = defaultdict(list)

    for report_path in all_reports:
        try:
            result = filter_report_to_original_prompts(report_path, original_ids)

            # Skip if not enough prompts analyzed
            if result['num_prompts'] < 60:  # Allow some missing but most should be there
                continue

            # Extract model name and temperature
            model_name = result['model']

            # Determine temperature
            if '_temp' in model_name:
                base_model = model_name.split('_temp')[0]
                temp = model_name.split('_temp')[1]
                temp_label = f"temp{temp}"
            else:
                # Baseline (default temperature - usually 0.2)
                base_model = model_name
                temp_label = "baseline"

            models[base_model].append({
                'temp': temp_label,
                'score': result['score'],
                'max_score': result['max_score'],
                'percentage': result['percentage'],
                'num_prompts': result['num_prompts']
            })
        except Exception as e:
            print(f"Error processing {report_path}: {e}")

    # Print results
    print("=" * 100)
    print("TEMPERATURE STUDY RESULTS - ORIGINAL 66 PROMPTS (Python + JavaScript Only)")
    print("=" * 100)
    print()

    # Sort models by best performance
    model_list = []
    for base_model in sorted(models.keys()):
        variants = models[base_model]

        # Skip if only one variant (no temperature study)
        if len(variants) < 2:
            continue

        # Get best score
        best_pct = max(v['percentage'] for v in variants)
        model_list.append((base_model, best_pct, variants))

    # Sort by best performance descending
    model_list.sort(key=lambda x: x[1], reverse=True)

    for base_model, best_pct, variants in model_list:
        # Sort by temperature
        temp_order = ['temp0.0', 'baseline', 'temp0.2', 'temp0.5', 'temp0.7', 'temp1.0']
        variants.sort(key=lambda x: temp_order.index(x['temp']) if x['temp'] in temp_order else 99)

        print(f"\n{base_model}")
        print("-" * 100)

        for v in variants:
            temp_display = v['temp'].replace('temp', 'Temperature ') if 'temp' in v['temp'] else 'Baseline (temp 0.2)'
            print(f"  {temp_display:25} {v['score']:3}/{v['max_score']} ({v['percentage']:5.1f}%)  [{v['num_prompts']} prompts]")

        # Calculate variation
        percentages = [v['percentage'] for v in variants]
        variation = max(percentages) - min(percentages)
        best = max(variants, key=lambda x: x['percentage'])
        worst = min(variants, key=lambda x: x['percentage'])

        print()
        print(f"  Variation: {variation:.1f} percentage points")
        print(f"  Best: {best['temp']} ({best['percentage']:.1f}%)")
        print(f"  Worst: {worst['temp']} ({worst['percentage']:.1f}%)")

    print()
    print("=" * 100)
    print(f"SUMMARY")
    print("=" * 100)
    print(f"Analysis based on {len(original_ids)} original prompts (Python + JavaScript only)")
    print(f"This excludes the 74 multi-language prompts added later (Java, C#, C/C++, Go, Rust)")
    print(f"")
    print(f"Models with temperature studies: {len(model_list)}")
    print("=" * 100)

if __name__ == "__main__":
    analyze_temperature_study()
