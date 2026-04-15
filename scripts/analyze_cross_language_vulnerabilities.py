#!/usr/bin/env python3
"""
Analyze Cross-Language Vulnerability Distribution
Shows which vulnerability categories appear in which programming languages
"""

import json
import os
from pathlib import Path
from collections import defaultdict
import csv

# Language mapping
LANGUAGE_MAP = {
    'py': 'Python',
    'js': 'JavaScript',
    'ts': 'TypeScript',
    'java': 'Java',
    'go': 'Go',
    'rs': 'Rust',
    'cpp': 'C++',
    'c': 'C',
    'cs': 'C#',
    'rb': 'Ruby',
    'php': 'PHP',
    'swift': 'Swift',
    'kt': 'Kotlin',
    'scala': 'Scala',
    'dart': 'Dart',
    'pl': 'Perl',
    'ex': 'Elixir',
    'exs': 'Elixir',
    'lua': 'Lua',
    'groovy': 'Groovy',
    'sol': 'Solidity',
    'Dockerfile': 'Dockerfile',
    'yaml': 'YAML',
    'yml': 'YAML',
    'tf': 'Terraform',
    'json': 'JSON',
    'xml': 'XML',
    'conf': 'Config',
    'sh': 'Shell',
    'bash': 'Bash',
    'txt': 'Text',
    'md': 'Markdown'
}

def get_language_from_filename(filename):
    """Extract language from filename"""
    if filename == 'Dockerfile':
        return 'Dockerfile'
    elif '.' in filename:
        ext = filename.split('.')[-1]
        return LANGUAGE_MAP.get(ext, ext.upper())
    return 'Unknown'

def analyze_cross_language_vulnerabilities():
    """Analyze vulnerability distribution across programming languages"""

    # Find baseline model directories
    output_dir = Path('output')
    model_dirs = []

    for model_dir in sorted(output_dir.glob('*')):
        if model_dir.is_dir():
            model_name = model_dir.name
            if '_temp' not in model_name and '_level' not in model_name and model_name != 'scripts':
                file_count = len([f for f in model_dir.glob('*') if f.is_file()])
                if file_count >= 700:
                    model_dirs.append(model_dir)

    print(f"Analyzing cross-language vulnerabilities for {len(model_dirs)} baseline models...")

    # Load all analysis reports
    all_results = {}
    for model_dir in model_dirs:
        model_name = model_dir.name
        report_file = Path('reports') / f'{model_name}_analysis.json'

        if report_file.exists():
            with open(report_file) as f:
                all_results[model_name] = json.load(f)

    # Cross-reference: category -> language -> {secure, vulnerable, total}
    category_language_stats = defaultdict(lambda: defaultdict(lambda: {
        'secure': 0, 'vulnerable': 0, 'refused': 0, 'total': 0
    }))

    # Language -> category -> {secure, vulnerable, total}
    language_category_stats = defaultdict(lambda: defaultdict(lambda: {
        'secure': 0, 'vulnerable': 0, 'refused': 0, 'total': 0
    }))

    # Process each model's results
    for model_name, data in all_results.items():
        # Process each test result
        for result in data.get('detailed_results', []):
            category = result['category']

            # Get language directly from the analysis report
            language_raw = result.get('language', 'unknown')

            # Map to proper display name (e.g., 'python' → 'Python')
            language = LANGUAGE_MAP.get(language_raw, language_raw.capitalize() if language_raw else 'Unknown')

            # Skip non-programming languages for vulnerability analysis
            if language in ['YAML', 'JSON', 'Text', 'Markdown', 'Unknown']:
                continue

            score = result.get('score', 0)
            max_score = result.get('max_score', 2)

            # Check if UNSUPPORTED
            is_refused = False
            for vuln in result.get('vulnerabilities', []):
                if isinstance(vuln, dict) and vuln.get('type') == 'UNSUPPORTED':
                    is_refused = True
                    break
                elif 'UNSUPPORTED' in str(vuln):
                    is_refused = True
                    break

            # Update stats
            category_language_stats[category][language]['total'] += 1
            language_category_stats[language][category]['total'] += 1

            if is_refused:
                category_language_stats[category][language]['refused'] += 1
                language_category_stats[language][category]['refused'] += 1
            elif score == max_score:
                category_language_stats[category][language]['secure'] += 1
                language_category_stats[language][category]['secure'] += 1
            else:
                category_language_stats[category][language]['vulnerable'] += 1
                language_category_stats[language][category]['vulnerable'] += 1

    # Export 1: Vulnerability by Language Matrix
    csv_path = Path('reports/vulnerability_by_language_matrix.csv')

    # Get all languages and categories
    all_languages = sorted(set(lang for cat_stats in category_language_stats.values()
                               for lang in cat_stats.keys()))
    all_categories = sorted(category_language_stats.keys())

    with open(csv_path, 'w', newline='') as f:
        writer = csv.writer(f)

        # Header
        header = ['Category', 'Total Tests']
        for lang in all_languages:
            header.extend([f'{lang} Secure', f'{lang} Vulnerable', f'{lang} Total', f'{lang} %'])
        writer.writerow(header)

        # Data rows
        for category in all_categories:
            lang_stats = category_language_stats[category]
            total_tests = sum(stats['total'] for stats in lang_stats.values())

            row = [category, total_tests]

            for lang in all_languages:
                stats = lang_stats.get(lang, {'secure': 0, 'vulnerable': 0, 'refused': 0, 'total': 0})
                tested = stats['secure'] + stats['vulnerable']
                pct = (stats['secure'] / tested * 100) if tested > 0 else 0

                row.extend([
                    stats['secure'],
                    stats['vulnerable'],
                    stats['total'],
                    f"{pct:.1f}"
                ])

            writer.writerow(row)

    print(f"✅ Generated: {csv_path}")

    # Export 2: Language by Vulnerability Matrix (transposed)
    csv_path2 = Path('reports/language_by_vulnerability_matrix.csv')

    with open(csv_path2, 'w', newline='') as f:
        writer = csv.writer(f)

        # Header
        header = ['Language', 'Total Tests', 'Total Secure', 'Total Vulnerable', 'Security %']
        for category in all_categories[:20]:  # Top 20 categories
            header.append(f'{category} %')
        writer.writerow(header)

        # Data rows
        for lang in all_languages:
            cat_stats = language_category_stats[lang]
            total_tests = sum(stats['total'] for stats in cat_stats.values())
            total_secure = sum(stats['secure'] for stats in cat_stats.values())
            total_vulnerable = sum(stats['vulnerable'] for stats in cat_stats.values())
            total_tested = total_secure + total_vulnerable
            overall_pct = (total_secure / total_tested * 100) if total_tested > 0 else 0

            row = [lang, total_tests, total_secure, total_vulnerable, f"{overall_pct:.1f}"]

            for category in all_categories[:20]:
                stats = cat_stats.get(category, {'secure': 0, 'vulnerable': 0, 'total': 0})
                tested = stats['secure'] + stats['vulnerable']
                pct = (stats['secure'] / tested * 100) if tested > 0 else 0
                row.append(f"{pct:.1f}")

            writer.writerow(row)

    print(f"✅ Generated: {csv_path2}")

    # Export 3: Language-Specific Vulnerability Hotspots
    csv_path3 = Path('reports/language_vulnerability_hotspots.csv')

    with open(csv_path3, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Language', 'Most Vulnerable Category', 'Vulnerability Rate %',
                        'Vulnerable Count', 'Total Tested'])

        for lang in sorted(all_languages):
            cat_stats = language_category_stats[lang]

            # Find most vulnerable category for this language
            worst_category = None
            worst_vuln_rate = 0
            worst_stats = {}

            for category, stats in cat_stats.items():
                tested = stats['secure'] + stats['vulnerable']
                if tested >= 5:  # At least 5 tests
                    vuln_rate = (stats['vulnerable'] / tested * 100) if tested > 0 else 0
                    if vuln_rate > worst_vuln_rate:
                        worst_vuln_rate = vuln_rate
                        worst_category = category
                        worst_stats = stats

            if worst_category:
                tested = worst_stats['secure'] + worst_stats['vulnerable']
                writer.writerow([
                    lang,
                    worst_category,
                    f"{worst_vuln_rate:.1f}",
                    worst_stats['vulnerable'],
                    tested
                ])

    print(f"✅ Generated: {csv_path3}")

    # Print summary
    print()
    print("=" * 80)
    print("CROSS-LANGUAGE VULNERABILITY DISTRIBUTION SUMMARY")
    print("=" * 80)
    print()

    print(f"Total programming languages analyzed: {len(all_languages)}")
    print(f"Total vulnerability categories: {len(all_categories)}")
    print()

    # Top 5 most vulnerable categories across all languages
    print("Top 5 Most Vulnerable Categories (Across All Languages):")
    category_vuln_rates = []
    for category, lang_stats in category_language_stats.items():
        total_secure = sum(stats['secure'] for stats in lang_stats.values())
        total_vulnerable = sum(stats['vulnerable'] for stats in lang_stats.values())
        total_tested = total_secure + total_vulnerable
        if total_tested >= 20:  # At least 20 tests
            vuln_rate = (total_vulnerable / total_tested * 100) if total_tested > 0 else 0
            category_vuln_rates.append((category, vuln_rate, total_vulnerable, total_tested))

    category_vuln_rates.sort(key=lambda x: x[1], reverse=True)
    for i, (category, rate, vuln, total) in enumerate(category_vuln_rates[:5], 1):
        print(f"  {i}. {category:<45} {rate:5.1f}% ({vuln}/{total})")

    print()

    # Language security rankings
    print("Language Security Rankings (by overall secure %):")
    lang_security = []
    for lang, cat_stats in language_category_stats.items():
        total_secure = sum(stats['secure'] for stats in cat_stats.values())
        total_vulnerable = sum(stats['vulnerable'] for stats in cat_stats.values())
        total_tested = total_secure + total_vulnerable
        if total_tested >= 50:  # At least 50 tests
            security_pct = (total_secure / total_tested * 100) if total_tested > 0 else 0
            lang_security.append((lang, security_pct, total_secure, total_tested))

    lang_security.sort(key=lambda x: x[1], reverse=True)
    for i, (lang, pct, secure, total) in enumerate(lang_security[:10], 1):
        print(f"  {i:2d}. {lang:<20} {pct:5.1f}% ({secure}/{total})")

    print()
    print("=" * 80)

if __name__ == '__main__':
    analyze_cross_language_vulnerabilities()
