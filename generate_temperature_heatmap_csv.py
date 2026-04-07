#!/usr/bin/env python3
"""
Generate CSV file for temperature study heat map visualization.
Output can be imported into Excel for heat map creation.
"""

import json
import glob
import csv
from collections import defaultdict

def generate_temperature_heatmap_csv():
    """Generate CSV with temperature data for heat map visualization."""

    # Find all temperature variant reports and baseline reports
    temp_reports = glob.glob("reports/*_temp*.json")

    # Also get baseline reports (models without temp/level variants)
    baseline_models = [
        'deepseek-coder', 'starcoder2', 'claude-opus-4-6', 'claude-sonnet-4-5',
        'codegemma', 'codellama', 'gpt-3.5-turbo', 'gpt-4', 'gpt-4o', 'gpt-4o-mini',
        'gpt-5.2', 'gpt-5.4', 'gpt-5.4-mini', 'gemini-2.5-flash', 'llama3.1',
        'mistral', 'qwen2.5-coder', 'qwen2.5-coder_14b', 'deepseek-coder_6.7b-instruct',
        'qwen3-coder_30b'
    ]

    for model in baseline_models:
        baseline = glob.glob(f"reports/{model}.json")
        temp_reports.extend(baseline)

    # Group by base model
    models = defaultdict(dict)

    for report_path in temp_reports:
        try:
            with open(report_path) as f:
                data = json.load(f)

            summary = data.get('summary', {})
            model_name = data.get('model_name', 'Unknown')

            # Use overall score from summary (already calculated)
            overall_score = summary.get('overall_score', '0/0')
            if '/' in overall_score:
                total_score, max_score = overall_score.split('/')
                total_score = int(total_score)
                max_score = int(max_score)
            else:
                total_score = 0
                max_score = 0

            if max_score == 0:
                continue

            percentage = summary.get('percentage', 0.0)

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
    temp_headers = ['Temperature 0.0', 'Temperature 0.2 (Baseline)', 'Temperature 0.5', 'Temperature 0.7', 'Temperature 1.0']

    # Generate CSV
    csv_file = 'TEMPERATURE_STUDY_HEATMAP.csv'

    with open(csv_file, 'w', newline='') as f:
        writer = csv.writer(f)

        # Header row
        writer.writerow(['Model'] + temp_headers + ['Min', 'Max', 'Variation'])

        # Data rows
        for base_model, best_pct, temps in model_list:
            row = [base_model]

            scores = []
            for temp in temp_order:
                if temp in temps:
                    pct = temps[temp]
                    row.append(f"{pct:.1f}")
                    scores.append(pct)
                else:
                    row.append('')

            # Add statistics
            if scores:
                row.append(f"{min(scores):.1f}")
                row.append(f"{max(scores):.1f}")
                row.append(f"{max(scores) - min(scores):.1f}")
            else:
                row.extend(['', '', ''])

            writer.writerow(row)

    print(f"CSV file generated: {csv_file}")
    print()
    print("To create a heat map in Excel:")
    print("1. Open the CSV file in Excel")
    print("2. Select the temperature data columns (B through F)")
    print("3. Go to Home > Conditional Formatting > Color Scales")
    print("4. Choose a color scale (Red-Yellow-Green or Red-White-Blue)")
    print("5. Red = low security, Green/Blue = high security")
    print()
    print(f"Total models: {len(model_list)}")
    print(f"Temperature range: 0.0 to 1.0")
    if model_list:
        print(f"Best performer: {model_list[0][0]} ({model_list[0][1]:.1f}%)")
    else:
        print("No models with temperature studies found")

    return csv_file

if __name__ == "__main__":
    generate_temperature_heatmap_csv()
