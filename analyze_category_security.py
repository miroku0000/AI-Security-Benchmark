#!/usr/bin/env python3
"""
Analyze security performance by specific vulnerability category
Shows security percentage for each category (SQL Injection, XSS, etc.) per model
Can be rerun when new data is available
"""
import json
import csv
from pathlib import Path
from collections import defaultdict
from typing import Dict, List

def is_unsupported(result: Dict) -> bool:
    """Check if result is UNSUPPORTED (refused to generate code)"""
    vulns = result.get('vulnerabilities', [])
    for v in vulns:
        if isinstance(v, dict) and v.get('type') == 'UNSUPPORTED':
            return True
        elif 'UNSUPPORTED' in str(v):
            return True
    return False

def analyze_model_by_category(json_file: Path) -> Dict:
    """Analyze a model's security performance by category"""
    with open(json_file, 'r') as f:
        data = json.load(f)

    model_name = data.get('model_name', json_file.stem.replace('_analysis', ''))

    # Initialize category statistics
    category_stats = defaultdict(lambda: {
        'total': 0, 'secure': 0, 'vulnerable': 0, 'refused': 0
    })

    # Process each result
    for result in data['detailed_results']:
        category = result['category']
        score = result.get('score', 0)
        max_score = result.get('max_score', 2)

        category_stats[category]['total'] += 1

        if is_unsupported(result):
            category_stats[category]['refused'] += 1
        elif score == max_score:
            category_stats[category]['secure'] += 1
        else:
            category_stats[category]['vulnerable'] += 1

    # Calculate percentages
    category_percentages = {}
    for category, stats in category_stats.items():
        tested = stats['secure'] + stats['vulnerable']  # Exclude refused
        if tested > 0:
            percentage = (stats['secure'] / tested) * 100
        else:
            percentage = None  # None = no tests completed

        category_percentages[category] = {
            'total_tests': stats['total'],
            'secure': stats['secure'],
            'vulnerable': stats['vulnerable'],
            'refused': stats['refused'],
            'tested': tested,
            'security_percentage': percentage
        }

    return {
        'model': model_name,
        'categories': category_percentages,
        'overall_summary': data['summary']
    }

def format_category_name(category: str) -> str:
    """Format category name for display"""
    # Convert snake_case to Title Case
    return ' '.join(word.capitalize() for word in category.split('_'))

def main():
    reports_dir = Path('reports')

    # Find all analysis JSON files (base models only)
    analysis_files = []
    for file in sorted(reports_dir.glob('*_analysis.json')):
        name = file.stem.replace('_analysis', '')
        # Skip temperature, level variants, and iteration reports
        if '_temp' not in name and '_level' not in name and 'iteration' not in name:
            analysis_files.append(file)

    if not analysis_files:
        print("No analysis files found!")
        return

    print(f"Analyzing {len(analysis_files)} models by vulnerability category...")
    print()

    # Analyze each model
    results = []
    for file in analysis_files:
        try:
            result = analyze_model_by_category(file)
            results.append(result)
        except Exception as e:
            print(f"Error analyzing {file}: {e}")

    # Sort by overall security score (from summary)
    results.sort(key=lambda x: x['overall_summary']['percentage'], reverse=True)

    # Get all categories that appear in any model
    all_categories = set()
    for result in results:
        all_categories.update(result['categories'].keys())
    all_categories = sorted(all_categories)

    # Print summary table
    print("=" * 150)
    print("SECURITY PERFORMANCE BY VULNERABILITY CATEGORY")
    print("=" * 150)
    print()

    # Aggregate stats by category
    aggregate_categories = defaultdict(lambda: {'secure': 0, 'vulnerable': 0, 'refused': 0, 'total': 0})

    for result in results:
        for category, stats in result['categories'].items():
            aggregate_categories[category]['secure'] += stats['secure']
            aggregate_categories[category]['vulnerable'] += stats['vulnerable']
            aggregate_categories[category]['refused'] += stats['refused']
            aggregate_categories[category]['total'] += stats['total_tests']

    # Sort categories by percentage (most vulnerable first)
    sorted_cats = sorted(
        aggregate_categories.items(),
        key=lambda x: (x[1]['secure'] / max(1, x[1]['secure'] + x[1]['vulnerable'])) * 100
    )

    print(f"{'Category':<45} {'Security %':<12} {'Secure':<10} {'Vulnerable':<12} {'Refused':<10} {'Total Tests':<12}")
    print("-" * 150)

    for category, stats in sorted_cats:
        tested = stats['secure'] + stats['vulnerable']
        if tested > 0:
            pct = (stats['secure'] / tested) * 100
            cat_display = format_category_name(category)
            print(f"{cat_display:<45} {pct:>6.1f}%      {stats['secure']:<10} {stats['vulnerable']:<12} "
                  f"{stats['refused']:<10} {stats['total']:<12}")
        else:
            cat_display = format_category_name(category)
            print(f"{cat_display:<45} {'N/A':>11}   {stats['secure']:<10} {stats['vulnerable']:<12} "
                  f"{stats['refused']:<10} {stats['total']:<12}")

    # Detailed per-model breakdown
    print()
    print("=" * 150)
    print("PER-MODEL CATEGORY BREAKDOWN")
    print("=" * 150)

    for result in results:
        print()
        print(f"\n{'=' * 100}")
        print(f"MODEL: {result['model']}")
        print(f"Overall Score: {result['overall_summary']['percentage']:.1f}% "
              f"({result['overall_summary']['secure']}/{result['overall_summary']['secure'] + result['overall_summary']['vulnerable']} tests)")
        print(f"{'=' * 100}")
        print()

        # Sort categories by security percentage (lowest first = most vulnerable)
        sorted_model_cats = sorted(
            result['categories'].items(),
            key=lambda x: x[1]['security_percentage'] if x[1]['security_percentage'] is not None else -1
        )

        print(f"{'Category':<45} {'Status':<15} {'Score':<10} {'Details':<50}")
        print("-" * 100)

        for category, stats in sorted_model_cats:
            if stats['security_percentage'] is None:
                status = "⚠️  ALL REFUSED"
                score = "N/A"
            elif stats['security_percentage'] >= 90:
                status = "✅ EXCELLENT"
                score = f"{stats['security_percentage']:.1f}%"
            elif stats['security_percentage'] >= 75:
                status = "✓  GOOD"
                score = f"{stats['security_percentage']:.1f}%"
            elif stats['security_percentage'] >= 60:
                status = "⚠  FAIR"
                score = f"{stats['security_percentage']:.1f}%"
            else:
                status = "❌ NEEDS WORK"
                score = f"{stats['security_percentage']:.1f}%"

            details = f"({stats['secure']} secure, {stats['vulnerable']} vuln, {stats['refused']} refused / {stats['total_tests']} total)"
            cat_display = format_category_name(category)
            print(f"{cat_display:<45} {status:<15} {score:<10} {details:<50}")

    # Export to CSV - Per-model breakdown
    csv_file = reports_dir / 'category_security_by_model.csv'
    with open(csv_file, 'w', newline='') as f:
        # Create header with all categories
        header = ['Model', 'Overall Score']
        for category in all_categories:
            cat_display = format_category_name(category)
            header.extend([f'{cat_display} %', f'{cat_display} (Secure/Tested)'])

        writer = csv.writer(f)
        writer.writerow(header)

        # Write data for each model
        for result in results:
            row = [
                result['model'],
                f"{result['overall_summary']['percentage']:.1f}%"
            ]

            for category in all_categories:
                stats = result['categories'].get(category)
                if stats is None:
                    row.extend(['N/A', 'N/A'])
                elif stats['security_percentage'] is None:
                    row.extend(['ALL REFUSED', f"0/{stats['total_tests']}"])
                else:
                    row.extend([
                        f"{stats['security_percentage']:.1f}%",
                        f"{stats['secure']}/{stats['tested']}"
                    ])

            writer.writerow(row)

    print()
    print(f"✅ Per-model CSV exported to: {csv_file}")

    # Export aggregate category stats
    aggregate_csv = reports_dir / 'category_aggregate_analysis.csv'
    with open(aggregate_csv, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Category', 'Security %', 'Secure', 'Vulnerable', 'Refused', 'Total Tests'])

        for category, stats in sorted_cats:
            tested = stats['secure'] + stats['vulnerable']
            if tested > 0:
                pct = (stats['secure'] / tested) * 100
                cat_display = format_category_name(category)
                writer.writerow([
                    cat_display,
                    f"{pct:.1f}%",
                    stats['secure'],
                    stats['vulnerable'],
                    stats['refused'],
                    stats['total']
                ])
            else:
                cat_display = format_category_name(category)
                writer.writerow([
                    cat_display,
                    'N/A',
                    stats['secure'],
                    stats['vulnerable'],
                    stats['refused'],
                    stats['total']
                ])

    print(f"✅ Aggregate CSV exported to: {aggregate_csv}")

    # Key insights
    print()
    print("=" * 150)
    print("KEY INSIGHTS")
    print("=" * 150)
    print()

    # Find weakest categories
    weakest_categories = sorted_cats[:5]
    print("Top 5 Most Vulnerable Categories (Across All Models):")
    for i, (category, stats) in enumerate(weakest_categories, 1):
        tested = stats['secure'] + stats['vulnerable']
        if tested > 0:
            pct = (stats['secure'] / tested) * 100
            cat_display = format_category_name(category)
            print(f"  {i}. {cat_display}: {pct:.1f}% secure ({stats['vulnerable']} vulnerabilities across {len(results)} models)")

    print()

    # Find strongest categories
    strongest_categories = sorted_cats[-5:][::-1]
    print("Top 5 Most Secure Categories (Across All Models):")
    for i, (category, stats) in enumerate(strongest_categories, 1):
        tested = stats['secure'] + stats['vulnerable']
        if tested > 0:
            pct = (stats['secure'] / tested) * 100
            cat_display = format_category_name(category)
            print(f"  {i}. {cat_display}: {pct:.1f}% secure ({stats['vulnerable']} vulnerabilities across {len(results)} models)")

if __name__ == '__main__':
    main()
