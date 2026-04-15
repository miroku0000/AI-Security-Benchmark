#!/usr/bin/env python3
"""Generate model rankings CSV with proper 'prompts' terminology."""

import json
import csv
from pathlib import Path

def load_analysis(report_path):
    """Load analysis report and extract key metrics."""
    try:
        with open(report_path) as f:
            data = json.load(f)

        summary = data.get('summary', {})

        # Handle both old and new report formats
        # "completed_tests" is actually completed prompts (each prompt = 1 test case)
        total = summary.get('completed_tests', summary.get('total_completed', 0))
        secure = summary.get('secure', 0)
        vulnerable = summary.get('vulnerable', 0)
        refused = summary.get('refused', 0)

        # Parse overall score (could be "936/1360" format or 68.82 percentage)
        overall_score = summary.get('overall_score', 0)
        if isinstance(overall_score, str) and '/' in overall_score:
            # Format: "936/1360" - convert to percentage
            parts = overall_score.split('/')
            numerator = float(parts[0])
            denominator = float(parts[1])
            overall_score = (numerator / denominator * 100) if denominator > 0 else 0
        elif 'percentage' in summary:
            overall_score = summary['percentage']

        return {
            'total': total,
            'secure': secure,
            'vulnerable': vulnerable,
            'refused': refused,
            'overall_score': float(overall_score)
        }
    except Exception as e:
        print(f"Error loading {report_path}: {e}")
        return None

def main():
    reports_dir = Path('reports')

    # Find all baseline model reports (exclude temp, level variants)
    model_scores = []

    for report_file in reports_dir.glob('*_analysis.json'):
        # Skip temperature and level studies
        if '_temp' in report_file.stem or '_level' in report_file.stem:
            continue

        # Extract model name
        model_name = report_file.stem.replace('_analysis', '')

        # Load analysis
        analysis = load_analysis(report_file)
        if analysis and analysis['total'] > 0:
            model_scores.append({
                'name': model_name,
                **analysis
            })

    # Sort by overall score (descending)
    model_scores.sort(key=lambda x: x['overall_score'], reverse=True)

    # Generate CSV
    csv_path = Path('reports/model_rankings.csv')
    with open(csv_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'rank', 'model', 'overall_score',
            'secure_count', 'secure_percentage',
            'vulnerable_count', 'vulnerable_percentage',
            'refused_count', 'refused_percentage',
            'total_prompts'
        ])
        writer.writeheader()

        for i, model in enumerate(model_scores, 1):
            secure_pct = (model['secure'] / model['total'] * 100) if model['total'] > 0 else 0
            vuln_pct = (model['vulnerable'] / model['total'] * 100) if model['total'] > 0 else 0
            refused_pct = (model['refused'] / model['total'] * 100) if model['total'] > 0 else 0

            writer.writerow({
                'rank': i,
                'model': model['name'],
                'overall_score': round(model['overall_score'], 1),
                'secure_count': model['secure'],
                'secure_percentage': round(secure_pct, 1),
                'vulnerable_count': model['vulnerable'],
                'vulnerable_percentage': round(vuln_pct, 1),
                'refused_count': model['refused'],
                'refused_percentage': round(refused_pct, 1),
                'total_prompts': model['total']
            })

    print(f"✅ Model rankings CSV generated: {csv_path}")
    print(f"📊 Total models ranked: {len(model_scores)}")
    if model_scores:
        print(f"🏆 Top model: {model_scores[0]['name']} ({model_scores[0]['overall_score']:.1f}%)")

if __name__ == '__main__':
    main()
