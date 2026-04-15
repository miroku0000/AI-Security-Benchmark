#!/usr/bin/env python3
"""
Generate language vulnerability summary table
Format: Language | Files | Vulnerable | Partial | Secure | Vuln Rate
"""

import json
from pathlib import Path
from collections import defaultdict
import csv

# Language mapping
LANGUAGE_MAP = {
    'py': 'Python',
    'python': 'Python',
    'js': 'JavaScript',
    'javascript': 'JavaScript',
    'ts': 'TypeScript',
    'typescript': 'TypeScript',
    'java': 'Java',
    'go': 'Go',
    'rs': 'Rust',
    'rust': 'Rust',
    'cpp': 'C++',
    'c++': 'C++',
    'c': 'C',
    'cs': 'C#',
    'csharp': 'C#',
    'rb': 'Ruby',
    'ruby': 'Ruby',
    'php': 'PHP',
    'swift': 'Swift',
    'kt': 'Kotlin',
    'kotlin': 'Kotlin',
    'scala': 'Scala',
    'dart': 'Dart',
    'pl': 'Perl',
    'perl': 'Perl',
    'ex': 'Elixir',
    'exs': 'Elixir',
    'elixir': 'Elixir',
    'lua': 'Lua',
    'groovy': 'Groovy',
    'sol': 'Solidity',
    'solidity': 'Solidity',
    'Dockerfile': 'Dockerfile',
    'dockerfile': 'Dockerfile',
    'yaml': 'YAML',
    'yml': 'YAML',
    'tf': 'Terraform',
    'terraform': 'Terraform',
    'json': 'JSON',
    'xml': 'XML',
    'conf': 'Config',
    'config': 'Config',
    'sh': 'Shell',
    'bash': 'Bash',
    'txt': 'Text',
    'md': 'Markdown'
}

def analyze_language_summary():
    """Generate language summary table with Files, Vulnerable, Partial, Secure counts"""

    # Find baseline model directories
    output_dir = Path('output')
    reports_dir = Path('reports')

    # Load all analysis reports
    all_results = {}
    for report_file in sorted(reports_dir.glob('*_analysis.json')):
        model_name = report_file.stem.replace('_analysis', '')

        # Skip temperature and level variants
        if '_temp' not in model_name and '_level' not in model_name and 'iteration' not in model_name:
            if report_file.exists():
                with open(report_file) as f:
                    all_results[model_name] = json.load(f)

    print(f"Analyzing language summary for {len(all_results)} baseline models...")

    # Language stats: {language: {vulnerable: 0, partial: 0, secure: 0, total: 0}}
    language_stats = defaultdict(lambda: {
        'vulnerable': 0,
        'partial': 0,
        'secure': 0,
        'total': 0
    })

    # Process each model's results
    for model_name, data in all_results.items():
        for result in data.get('detailed_results', []):
            # Get language directly from the analysis report
            language_raw = result.get('language', 'unknown')

            # Map to proper display name (e.g., 'python' → 'Python')
            language = LANGUAGE_MAP.get(language_raw.lower(), language_raw.capitalize() if language_raw else 'Unknown')

            # Skip non-programming languages and config files
            if language in ['YAML', 'JSON', 'Text', 'Markdown', 'Unknown', 'Dockerfile', 'Terraform', 'Config', 'Shell', 'Bash', 'XML']:
                continue

            score = result.get('score', 0)
            max_score = result.get('max_score', 2)

            # Check if UNSUPPORTED (refused)
            is_refused = False
            for vuln in result.get('vulnerabilities', []):
                if isinstance(vuln, dict) and vuln.get('type') == 'UNSUPPORTED':
                    is_refused = True
                    break
                elif 'UNSUPPORTED' in str(vuln):
                    is_refused = True
                    break

            if is_refused:
                continue  # Skip refused tests

            # Categorize as vulnerable, partial, or secure
            language_stats[language]['total'] += 1

            if score == 0:
                language_stats[language]['vulnerable'] += 1
            elif score == max_score:
                language_stats[language]['secure'] += 1
            else:
                language_stats[language]['partial'] += 1

    # Export CSV
    csv_path = reports_dir / 'language_summary.csv'
    with open(csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Language', 'Files', 'Vulnerable', 'Partial', 'Secure', 'Vuln Rate'])

        # Sort by total files (descending)
        sorted_languages = sorted(language_stats.items(), key=lambda x: x[1]['total'], reverse=True)

        for language, stats in sorted_languages:
            if stats['total'] == 0:
                continue

            vuln_rate = (stats['vulnerable'] / stats['total'] * 100) if stats['total'] > 0 else 0

            writer.writerow([
                language,
                stats['total'],
                stats['vulnerable'],
                stats['partial'],
                stats['secure'],
                f"{vuln_rate:.1f}%"
            ])

    print(f"✅ Generated: {csv_path}")

    # Print summary
    print()
    print("=" * 80)
    print("LANGUAGE VULNERABILITY SUMMARY")
    print("=" * 80)
    print()
    print(f"{'Language':<20} {'Files':<8} {'Vulnerable':<12} {'Partial':<10} {'Secure':<10} {'Vuln Rate':<12}")
    print("-" * 80)

    for language, stats in sorted_languages[:20]:  # Top 20
        if stats['total'] == 0:
            continue

        vuln_rate = (stats['vulnerable'] / stats['total'] * 100) if stats['total'] > 0 else 0

        print(f"{language:<20} {stats['total']:<8} {stats['vulnerable']:<12} {stats['partial']:<10} {stats['secure']:<10} {vuln_rate:>5.1f}%")

    print()
    print("=" * 80)

if __name__ == '__main__':
    analyze_language_summary()
