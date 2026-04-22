#!/usr/bin/env python3
"""
Generate most vulnerable category by language analysis
"""
import json
from pathlib import Path
from collections import defaultdict

def analyze_language_categories():
    reports_dir = Path('reports')

    # Base models (27 total)
    base_models = [
        'claude-code',
        'claude-opus-4-6',
        'claude-sonnet-4-5',
        'codegemma',
        'codellama',
        'codex-app-no-skill',
        'codex-app-security-skill',
        'cursor',
        'deepseek-coder',
        'deepseek-coder_6.7b-instruct',
        'gemini-2.5-flash',
        'gpt-3.5-turbo',
        'gpt-4',
        'gpt-4o',
        'gpt-4o-mini',
        'gpt-5.2',
        'gpt-5.4',
        'gpt-5.4-mini',
        'llama3.1',
        'mistral',
        'o1',
        'o3',
        'o3-mini',
        'qwen2.5-coder',
        'qwen2.5-coder_14b',
        'qwen3-coder_30b',
        'starcoder2'
    ]

    # Language -> Category -> {total, vulnerable}
    language_category_stats = defaultdict(lambda: defaultdict(lambda: {'total': 0, 'vulnerable': 0}))

    for model in base_models:
        report_file = reports_dir / f'{model}.json'
        if not report_file.exists():
            continue

        with open(report_file) as f:
            data = json.load(f)

        for result in data.get('detailed_results', []):
            language = result.get('language', 'unknown')
            category = result.get('category', 'unknown')
            primary_result = result.get('primary_detector_result', '')

            # Normalize language names
            language = language.lower()
            if language in ['yml', 'yaml']:
                language = 'yaml'
            elif language in ['dockerfile', 'docker']:
                language = 'dockerfile'
            elif language in ['hcl', 'terraform']:
                language = 'terraform'
            elif language in ['ts', 'typescript']:
                language = 'typescript'
            elif language in ['js', 'javascript']:
                language = 'javascript'
            elif language in ['sh', 'shell', 'bash']:
                language = 'bash'
            elif language in ['py', 'python']:
                language = 'python'
            elif language in ['rb', 'ruby']:
                language = 'ruby'
            elif language in ['conf', 'config']:
                language = 'conf'

            language_category_stats[language][category]['total'] += 1

            # Check for vulnerabilities (primary FAIL or actual vulnerability findings)
            score = result.get('score', 0)
            max_score = result.get('max_score', 2)

            has_real_vulns = any(
                v.get('type') not in ['SECURE', 'UNSUPPORTED']
                for v in result.get('vulnerabilities', [])
                if isinstance(v, dict)
            )

            if primary_result == 'FAIL' or score < max_score or has_real_vulns:
                language_category_stats[language][category]['vulnerable'] += 1

    # For each language, find the most vulnerable category
    language_worst_categories = []

    for language, categories in language_category_stats.items():
        worst_category = None
        worst_rate = 0
        worst_stats = None

        for category, stats in categories.items():
            if stats['total'] > 0:
                vuln_rate = (stats['vulnerable'] / stats['total'] * 100)

                # Find the category with highest vulnerability rate
                # (and enough samples to be meaningful)
                if vuln_rate > worst_rate and stats['total'] >= 2:
                    worst_rate = vuln_rate
                    worst_category = category
                    worst_stats = stats

        if worst_category:
            language_worst_categories.append({
                'language': language,
                'category': worst_category,
                'rate': worst_rate,
                'vulnerable': worst_stats['vulnerable'],
                'total': worst_stats['total']
            })

    # Sort by language name
    language_worst_categories.sort(key=lambda x: x['language'])

    # Print summary
    print("=" * 100)
    print("MOST VULNERABLE CATEGORY BY LANGUAGE")
    print("=" * 100)
    print()

    print(f"{'Language':<15} {'Most Vulnerable Category':<35} {'Rate':<8} {'Vuln':<6} {'Total':<6}")
    print("-" * 100)

    for item in language_worst_categories:
        lang_display = item['language'].capitalize()
        print(f"{lang_display:<15} {item['category']:<35} {item['rate']:>6.1f}% {item['vulnerable']:>5} {item['total']:>5}")

    print()

    # Save to CSV
    csv_path = 'reports/language_worst_category.csv'
    with open(csv_path, 'w') as f:
        f.write('Language,Most Vulnerable Category,Vulnerability Rate %,Vulnerable Count,Total Tested\n')

        for item in language_worst_categories:
            lang_display = item['language'].capitalize()
            f.write(f"{lang_display},{item['category']},{item['rate']:.1f}%,{item['vulnerable']},{item['total']}\n")

    print(f'✅ Language worst category analysis saved to: {csv_path}')
    print()

    # Additional statistics
    print("=" * 100)
    print("KEY INSIGHTS")
    print("=" * 100)
    print()

    # Find categories that are 100% vulnerable
    perfect_fails = [item for item in language_worst_categories if item['rate'] >= 99.9]
    print(f"Languages with 100% vulnerable categories: {len(perfect_fails)}")
    for item in perfect_fails[:10]:
        print(f"  • {item['language'].capitalize()}: {item['category']} ({item['vulnerable']}/{item['total']})")

    print()

    # Find categories with 0% vulnerable
    perfect_passes = [item for item in language_worst_categories if item['rate'] < 1.0]
    print(f"Languages where worst category is <1% vulnerable: {len(perfect_passes)}")
    for item in perfect_passes:
        print(f"  • {item['language'].capitalize()}: {item['category']} ({item['vulnerable']}/{item['total']})")

if __name__ == '__main__':
    analyze_language_categories()
