#!/usr/bin/env python3
"""
Analyze temperature sensitivity across models
Creates a heatmap CSV showing security score changes across temperatures
"""
import json
from pathlib import Path
from collections import defaultdict
from typing import Dict, List
import csv

def parse_model_name(filename: str) -> Dict:
    """Parse model name to extract base model and temperature"""
    name = filename.replace('_analysis.json', '').replace('.json', '')

    info = {
        'full_name': name,
        'base_model': name,
        'temperature': None,
        'is_temp_variant': False
    }

    # Check for temperature variant
    if '_temp' in name:
        parts = name.split('_temp')
        info['base_model'] = parts[0]
        info['temperature'] = float(parts[1])
        info['is_temp_variant'] = True

    return info

def analyze_report(json_file: Path) -> Dict:
    """Analyze a single report and extract metrics"""
    with open(json_file, 'r') as f:
        data = json.load(f)

    model_info = parse_model_name(json_file.name)
    summary = data.get('summary', {})

    return {
        'model_info': model_info,
        'model_name': data.get('model_name', model_info['full_name']),
        'percentage': summary.get('percentage', 0.0),
        'score': summary.get('overall_score', '0/0'),
        'secure': summary.get('secure', 0),
        'vulnerable': summary.get('vulnerable', 0),
        'refused': summary.get('refused', 0)
    }

def main():
    reports_dir = Path('reports')

    # Find all analysis JSON files
    all_files = list(reports_dir.glob('*_analysis.json'))

    # Exclude iteration reports
    analysis_files = [f for f in all_files if 'iteration' not in f.name]

    if not analysis_files:
        print("No analysis files found!")
        return

    print(f"Analyzing {len(analysis_files)} configurations for temperature sensitivity...")
    print()

    # Parse all reports
    results = []
    for file in analysis_files:
        try:
            result = analyze_report(file)
            results.append(result)
        except Exception as e:
            print(f"Error analyzing {file}: {e}")

    # Group by base model
    by_base_model = defaultdict(list)
    for result in results:
        base = result['model_info']['base_model']
        by_base_model[base].append(result)

    # Identify models with temperature variants
    models_with_temps = {}
    for base_model, variants in by_base_model.items():
        temp_variants = [v for v in variants if v['model_info']['is_temp_variant']]
        if temp_variants:
            # Include base model (assumed temp=1.0 if no explicit temp)
            base_variant = [v for v in variants if not v['model_info']['is_temp_variant']]
            all_variants = temp_variants + base_variant

            # Assign default temperature to base model if needed
            for v in all_variants:
                if v['model_info']['temperature'] is None:
                    v['model_info']['temperature'] = 1.0

            models_with_temps[base_model] = sorted(all_variants, key=lambda x: x['model_info']['temperature'])

    if not models_with_temps:
        print("No temperature variants found!")
        print("Temperature variants should be named like: model_temp0.0, model_temp0.5, etc.")
        return

    # Collect all unique temperatures
    all_temps = set()
    for variants in models_with_temps.values():
        for v in variants:
            all_temps.add(v['model_info']['temperature'])
    all_temps = sorted(all_temps)

    # Calculate sensitivity metrics
    sensitivity_data = []
    for base_model, variants in models_with_temps.items():
        temps = [v['model_info']['temperature'] for v in variants]
        scores = [v['percentage'] for v in variants]

        # Calculate sensitivity metrics
        score_range = max(scores) - min(scores)
        best_temp = temps[scores.index(max(scores))]
        worst_temp = temps[scores.index(min(scores))]
        avg_score = sum(scores) / len(scores)

        # Calculate standard deviation
        variance = sum((s - avg_score) ** 2 for s in scores) / len(scores)
        std_dev = variance ** 0.5

        sensitivity_data.append({
            'model': base_model,
            'num_temps': len(variants),
            'score_range': score_range,
            'std_dev': std_dev,
            'avg_score': avg_score,
            'best_temp': best_temp,
            'best_score': max(scores),
            'worst_temp': worst_temp,
            'worst_score': min(scores),
            'variants': variants
        })

    # Sort by sensitivity (score range, descending)
    sensitivity_data.sort(key=lambda x: x['score_range'], reverse=True)

    # Print sensitivity ranking
    print("=" * 120)
    print("TEMPERATURE SENSITIVITY RANKING")
    print("=" * 120)
    print()
    print(f"{'Rank':<6} {'Model':<35} {'Score Range':<15} {'Std Dev':<12} {'Best Temp':<12} {'Worst Temp':<12}")
    print("-" * 120)

    for i, data in enumerate(sensitivity_data, 1):
        print(f"{i:<6} {data['model']:<35} {data['score_range']:>6.2f}%        "
              f"{data['std_dev']:>6.2f}%     {data['best_temp']:>5.1f}        {data['worst_temp']:>5.1f}")

    print()

    # Create heatmap CSV
    heatmap_csv = reports_dir / 'temperature_sensitivity_heatmap.csv'
    with open(heatmap_csv, 'w', newline='') as f:
        writer = csv.writer(f)

        # Header row
        header = ['Model / Temperature →'] + [f'Temp {t:.1f}' for t in all_temps] + [
            'Score Range', 'Std Dev', 'Avg Score', 'Best Temp', 'Worst Temp'
        ]
        writer.writerow(header)

        # Data rows (sorted by sensitivity)
        for data in sensitivity_data:
            row = [data['model']]

            # Add scores for each temperature
            temp_to_score = {v['model_info']['temperature']: v['percentage']
                           for v in data['variants']}

            for temp in all_temps:
                if temp in temp_to_score:
                    row.append(f"{temp_to_score[temp]:.2f}%")
                else:
                    row.append('N/A')

            # Add summary statistics
            row.extend([
                f"{data['score_range']:.2f}%",
                f"{data['std_dev']:.2f}%",
                f"{data['avg_score']:.2f}%",
                f"{data['best_temp']:.1f}",
                f"{data['worst_temp']:.1f}"
            ])

            writer.writerow(row)

    print(f"✅ Temperature sensitivity heatmap exported to: {heatmap_csv}")
    print()

    # Detailed breakdown
    print("=" * 120)
    print("DETAILED TEMPERATURE ANALYSIS")
    print("=" * 120)

    for data in sensitivity_data:
        print()
        print(f"Model: {data['model']}")
        print(f"Score Range: {data['score_range']:.2f}% (High sensitivity)" if data['score_range'] > 5
              else f"Score Range: {data['score_range']:.2f}% (Low sensitivity)")
        print(f"Standard Deviation: {data['std_dev']:.2f}%")
        print()
        print(f"{'Temperature':<15} {'Security Score':<18} {'Secure':<10} {'Vulnerable':<12} {'Refused':<10}")
        print("-" * 80)

        for v in sorted(data['variants'], key=lambda x: x['model_info']['temperature']):
            temp = v['model_info']['temperature']
            score = v['percentage']
            secure = v['secure']
            vuln = v['vulnerable']
            refused = v['refused']

            # Highlight best and worst
            marker = ""
            if temp == data['best_temp']:
                marker = " 🏆 BEST"
            elif temp == data['worst_temp']:
                marker = " ⚠️  WORST"

            print(f"{temp:<15.1f} {score:>6.2f}%{marker:<12} {secure:<10} {vuln:<12} {refused:<10}")

        print()

    # Key insights
    print("=" * 120)
    print("KEY INSIGHTS")
    print("=" * 120)
    print()

    if sensitivity_data:
        most_sensitive = sensitivity_data[0]
        least_sensitive = sensitivity_data[-1]

        print(f"1. Most Temperature-Sensitive Model: {most_sensitive['model']}")
        print(f"   - Score varies by {most_sensitive['score_range']:.2f}% across temperatures")
        print(f"   - Best performance at temp={most_sensitive['best_temp']:.1f} ({most_sensitive['best_score']:.2f}%)")
        print(f"   - Worst performance at temp={most_sensitive['worst_temp']:.1f} ({most_sensitive['worst_score']:.2f}%)")
        print()

        print(f"2. Least Temperature-Sensitive Model: {least_sensitive['model']}")
        print(f"   - Score varies by only {least_sensitive['score_range']:.2f}% across temperatures")
        print(f"   - Consistent performance regardless of temperature")
        print()

        # Find optimal temperature across all models
        temp_performance = defaultdict(list)
        for data in sensitivity_data:
            for v in data['variants']:
                temp = v['model_info']['temperature']
                score = v['percentage']
                temp_performance[temp].append(score)

        avg_by_temp = {temp: sum(scores)/len(scores)
                      for temp, scores in temp_performance.items()}
        best_overall_temp = max(avg_by_temp.items(), key=lambda x: x[1])

        print(f"3. Optimal Temperature (Across All Models): {best_overall_temp[0]:.1f}")
        print(f"   - Average security score: {best_overall_temp[1]:.2f}%")
        print()

        # Temperature recommendations
        print("4. Temperature Recommendations by Model:")
        for data in sensitivity_data:
            improvement = data['best_score'] - data['worst_score']
            if improvement > 5:
                print(f"   - {data['model']}: Use temp={data['best_temp']:.1f} for {improvement:.1f}% improvement")
        print()

if __name__ == '__main__':
    main()
