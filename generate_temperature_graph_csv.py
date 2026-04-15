#!/usr/bin/env python3
"""
Generate CSV file optimized for graphing temperature study.
Temperatures on X-axis, models as separate lines.
"""

import json
import glob
import csv
from collections import defaultdict

def generate_temperature_graph_csv():
    """Generate CSV optimized for line graphs (temperatures as X-axis)."""

    # Find all temperature variant reports (66-prompt study)
    temp_reports = glob.glob("reports/*_temp*_20260323.json")

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
            with open(report_path) as f:
                data = json.load(f)

            model_name = data.get('model_name', 'Unknown')

            # Filter to 66-prompt results (208-point scale)
            import yaml
            with open('prompts/prompts.yaml') as pf:
                prompt_data = yaml.safe_load(pf)

            original_ids = set(
                p['id'] for p in prompt_data['prompts']
                if p.get('language') in ['python', 'javascript']
            )

            # Calculate score for 66 prompts only
            all_results = data.get('detailed_results', [])
            total_score = 0
            max_score = 0

            for result in all_results:
                prompt_id = result.get('prompt_id')
                if prompt_id in original_ids:
                    score = result.get('score', 0)
                    max_possible = result.get('max_score', 2)
                    total_score += score
                    max_score += max_possible

            if max_score == 0:
                continue

            percentage = (total_score / max_score * 100)

            # Determine temperature
            if '_temp' in model_name:
                base_model = model_name.split('_temp')[0]
                temp = model_name.split('_temp')[1]
            else:
                base_model = model_name
                temp = '0.2'  # Baseline is 0.2

            models[base_model][temp] = percentage

        except Exception as e:
            pass

    # Filter to models with temperature studies
    models_with_temps = {m: temps for m, temps in models.items() if len(temps) > 1}

    # Sort models by best performance
    model_list = []
    for base_model, temps in models_with_temps.items():
        best_pct = max(temps.values())
        model_list.append((base_model, best_pct, temps))

    model_list.sort(key=lambda x: x[1], reverse=True)

    # Temperature order
    temp_order = ['0.0', '0.2', '0.5', '0.7', '1.0']

    # Generate TRANSPOSED CSV (temperatures as rows, models as columns)
    csv_file = 'TEMPERATURE_STUDY_GRAPH.csv'

    with open(csv_file, 'w', newline='') as f:
        writer = csv.writer(f)

        # Header row: Temperature, then model names
        header = ['Temperature'] + [model[0] for model in model_list]
        writer.writerow(header)

        # Data rows: one per temperature
        for temp in temp_order:
            row = [temp]
            for base_model, best_pct, temps in model_list:
                if temp in temps:
                    row.append(f"{temps[temp]:.1f}")
                else:
                    row.append('')
            writer.writerow(row)

    print(f"CSV file generated: {csv_file}")
    print()
    print("To create a line graph in Excel:")
    print("1. Open the CSV file in Excel")
    print("2. Select ALL data (columns A through T, rows 1-6)")
    print("3. Go to Insert > Charts > Line")
    print("4. Choose 'Line with Markers'")
    print("5. Temperature will be on X-axis, security % on Y-axis")
    print("6. Each model will be a different colored line")
    print()
    print("Optional: To show only top performers:")
    print("- Select columns A through F (temperature + top 5 models)")
    print("- Insert > Line chart")
    print()
    print(f"Total models: {len(model_list)}")
    print(f"Top 5 models: {', '.join([m[0] for m in model_list[:5]])}")

    # Also generate a simplified version with just top 5 models
    csv_file_top5 = 'TEMPERATURE_STUDY_GRAPH_TOP5.csv'

    with open(csv_file_top5, 'w', newline='') as f:
        writer = csv.writer(f)

        # Header row: Temperature, then top 5 model names
        header = ['Temperature'] + [model[0] for model in model_list[:5]]
        writer.writerow(header)

        # Data rows: one per temperature
        for temp in temp_order:
            row = [temp]
            for base_model, best_pct, temps in model_list[:5]:
                if temp in temps:
                    row.append(f"{temps[temp]:.1f}")
                else:
                    row.append('')
            writer.writerow(row)

    print(f"\nAlso generated top 5 models only: {csv_file_top5}")
    print("(Cleaner graph with less clutter)")

    return csv_file, csv_file_top5

if __name__ == "__main__":
    generate_temperature_graph_csv()
