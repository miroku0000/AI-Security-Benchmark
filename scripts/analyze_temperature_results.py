#!/usr/bin/env python3
"""
Analyze temperature study results from all completed tests.
"""

import json
from pathlib import Path
from collections import defaultdict
import re

def extract_model_temp_from_filename(filename):
    """Extract model name and temperature from report filename."""
    # Format 1: modelname_temp0.0_208point_DATE.json
    match = re.match(r'(.+?)_temp([\d.]+)_208point', filename)
    if match:
        model = match.group(1)
        temp = float(match.group(2))
        return model, temp

    # Format 2: modelname_208point_20260320.json (default temp 0.2)
    match = re.match(r'(.+?)_208point_20260320\.json', filename)
    if match:
        model = match.group(1)
        temp = 0.2  # Default temperature
        return model, temp

    return None, None

def main():
    reports_dir = Path('reports')
    # Get explicit temp reports (temp0.0, temp0.5, etc.)
    temp_reports = list(reports_dir.glob('*temp*.json'))

    # Also get default reports (no temp in name = temp 0.2)
    # Only from March 20, 2026 to match the temperature study
    default_reports = list(reports_dir.glob('*_208point_20260320.json'))
    default_reports = [r for r in default_reports if 'temp' not in r.name]

    # Combine both sets
    all_reports = temp_reports + default_reports
    temp_reports = all_reports

    print("=" * 80)
    print("TEMPERATURE STUDY RESULTS ANALYSIS")
    print("=" * 80)
    print(f"Total reports found: {len(temp_reports)}")
    print()

    # Group by model
    model_results = defaultdict(dict)

    for report_file in temp_reports:
        model, temp = extract_model_temp_from_filename(report_file.name)
        if model is None:
            continue

        try:
            with open(report_file) as f:
                data = json.load(f)

            # Try to get score from summary section first
            summary = data.get('summary', {})
            if 'overall_score' in summary:
                # Parse "129/208" format
                score_str = summary['overall_score']
                if '/' in score_str:
                    score, max_score = map(int, score_str.split('/'))
                else:
                    score = int(score_str)
                    max_score = 208
            else:
                score = data.get('total_score', 0)
                max_score = data.get('max_score', 208)

            percentage = (score / max_score * 100) if max_score > 0 else 0

            model_results[model][temp] = {
                'score': score,
                'max_score': max_score,
                'percentage': percentage,
                'report': report_file.name
            }
        except Exception as e:
            print(f"Error reading {report_file.name}: {e}")
            continue

    # Analyze each model
    print("=" * 80)
    print("RESULTS BY MODEL")
    print("=" * 80)
    print()

    temperature_impact = []

    for model in sorted(model_results.keys()):
        temps = model_results[model]
        if len(temps) < 2:
            continue  # Need at least 2 temperatures to compare

        print(f"{model}")
        print("-" * 80)

        scores = []
        for temp in sorted(temps.keys()):
            result = temps[temp]
            score = result['score']
            percentage = result['percentage']
            scores.append(percentage)
            print(f"  Temp {temp:.1f}: {score}/{result['max_score']} ({percentage:.1f}%)")

        # Calculate variation
        if len(scores) >= 2:
            min_score = min(scores)
            max_score = max(scores)
            variation = max_score - min_score
            avg_score = sum(scores) / len(scores)

            print(f"  Variation: {variation:.1f} percentage points (range: {min_score:.1f}% - {max_score:.1f}%)")
            print(f"  Average: {avg_score:.1f}%")

            temperature_impact.append({
                'model': model,
                'variation': variation,
                'min': min_score,
                'max': max_score,
                'avg': avg_score,
                'num_temps': len(scores)
            })

        print()

    # Summary: Most temperature-sensitive models
    print("=" * 80)
    print("TEMPERATURE SENSITIVITY RANKING")
    print("=" * 80)
    print("(Models with largest variation across temperatures)")
    print()

    temperature_impact.sort(key=lambda x: x['variation'], reverse=True)

    print(f"{'Rank':<6} {'Model':<35} {'Variation':<12} {'Range':<25} {'Tests'}")
    print("-" * 80)

    for i, item in enumerate(temperature_impact, 1):
        model = item['model']
        variation = item['variation']
        min_score = item['min']
        max_score = item['max']
        num_temps = item['num_temps']

        print(f"{i:<6} {model:<35} {variation:>6.1f} pp    {min_score:>5.1f}% - {max_score:>5.1f}%    {num_temps} temps")

    print()
    print("=" * 80)
    print("SUMMARY STATISTICS")
    print("=" * 80)
    print(f"Total models tested: {len(model_results)}")
    print(f"Total reports analyzed: {len(temp_reports)}")
    print(f"Models with multiple temperatures: {len(temperature_impact)}")
    print()

    if temperature_impact:
        avg_variation = sum(x['variation'] for x in temperature_impact) / len(temperature_impact)
        print(f"Average temperature variation: {avg_variation:.1f} percentage points")

        most_sensitive = temperature_impact[0]
        least_sensitive = temperature_impact[-1]

        print(f"Most temperature-sensitive: {most_sensitive['model']} ({most_sensitive['variation']:.1f} pp)")
        print(f"Least temperature-sensitive: {least_sensitive['model']} ({least_sensitive['variation']:.1f} pp)")

    print()
    print("=" * 80)
    print("KEY FINDINGS")
    print("=" * 80)

    # Find patterns
    print()
    print("1. Models that improve with higher temperature:")
    improvers = [x for x in temperature_impact if x['max'] > x['min'] + 5.0]
    for item in improvers[:5]:
        print(f"   - {item['model']}: {item['min']:.1f}% → {item['max']:.1f}% (+{item['max'] - item['min']:.1f} pp)")

    print()
    print("2. Most stable models (< 5 pp variation):")
    stable = [x for x in temperature_impact if x['variation'] < 5.0]
    for item in stable[:5]:
        print(f"   - {item['model']}: {item['variation']:.1f} pp variation (avg: {item['avg']:.1f}%)")

    print()
    print("3. Top performers (by average score across temperatures):")
    by_avg = sorted(temperature_impact, key=lambda x: x['avg'], reverse=True)
    for item in by_avg[:10]:
        print(f"   - {item['model']}: {item['avg']:.1f}% average ({item['num_temps']} temps tested)")

    print()
    print("=" * 80)

if __name__ == '__main__':
    main()
