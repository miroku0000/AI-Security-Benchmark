#!/usr/bin/env python3
"""
Generate language breakdown CSV from code files
Properly categorizes languages instead of "Other"
"""

import json
import os
from pathlib import Path
from collections import defaultdict
import csv

# Language categorization
LANGUAGE_CATEGORIES = {
    'Programming Languages': {
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
        'sol': 'Solidity'
    },
    'Infrastructure & Config': {
        'Dockerfile': 'Dockerfile',
        'yaml': 'YAML',
        'yml': 'YAML',
        'tf': 'Terraform',
        'json': 'JSON',
        'xml': 'XML',
        'conf': 'Config',
        'sh': 'Shell',
        'bash': 'Bash'
    },
    'Documentation': {
        'txt': 'Text',
        'md': 'Markdown',
        'rst': 'reStructuredText'
    }
}

def categorize_extension(ext):
    """Categorize file extension"""
    for category, extensions in LANGUAGE_CATEGORIES.items():
        if ext in extensions:
            return category, extensions[ext]
    return 'Other', ext.upper() if ext else 'Unknown'

def analyze_language_breakdown():
    """Analyze language breakdown across all baseline models"""

    # Find all baseline model directories
    output_dir = Path('output')
    model_dirs = []

    for model_dir in sorted(output_dir.glob('*')):
        if model_dir.is_dir():
            model_name = model_dir.name
            # Skip temperature, level variants, and scripts
            if '_temp' not in model_name and '_level' not in model_name and model_name != 'scripts':
                file_count = len([f for f in model_dir.glob('*') if f.is_file()])
                if file_count >= 700:  # Only complete baseline models
                    model_dirs.append(model_dir)

    print(f"Analyzing language breakdown for {len(model_dirs)} baseline models...")

    # Collect language stats per model
    model_languages = {}

    for model_dir in model_dirs:
        model_name = model_dir.name
        language_counts = defaultdict(int)
        category_counts = defaultdict(int)

        for file_path in model_dir.glob('*'):
            if file_path.is_file():
                # Get extension
                if file_path.name == 'Dockerfile':
                    ext = 'Dockerfile'
                elif '.' in file_path.name:
                    ext = file_path.suffix.lstrip('.')
                else:
                    ext = 'no_extension'

                category, language = categorize_extension(ext)
                language_counts[language] += 1
                category_counts[category] += 1

        model_languages[model_name] = {
            'languages': dict(language_counts),
            'categories': dict(category_counts),
            'total_files': sum(language_counts.values())
        }

    # Get all unique languages across all models
    all_languages = set()
    all_categories = set()

    for model_data in model_languages.values():
        all_languages.update(model_data['languages'].keys())
        all_categories.update(model_data['categories'].keys())

    all_languages = sorted(all_languages)
    all_categories = sorted(all_categories)

    # Export per-language breakdown CSV
    csv_path = Path('reports/language_breakdown_detailed.csv')
    with open(csv_path, 'w', newline='') as f:
        writer = csv.writer(f)

        # Header
        header = ['Model', 'Total Files']
        for lang in all_languages:
            header.extend([f'{lang} Count', f'{lang} %'])
        writer.writerow(header)

        # Data rows
        for model_name in sorted(model_languages.keys(),
                                 key=lambda m: model_languages[m]['total_files'],
                                 reverse=True):
            data = model_languages[model_name]
            row = [model_name, data['total_files']]

            for lang in all_languages:
                count = data['languages'].get(lang, 0)
                pct = (count / data['total_files'] * 100) if data['total_files'] > 0 else 0
                row.extend([count, f"{pct:.1f}"])

            writer.writerow(row)

    print(f"✅ Generated: {csv_path}")

    # Export category-level breakdown CSV
    csv_path_cat = Path('reports/language_breakdown_categories.csv')
    with open(csv_path_cat, 'w', newline='') as f:
        writer = csv.writer(f)

        # Header
        header = ['Model', 'Total Files']
        for cat in all_categories:
            header.extend([f'{cat} Count', f'{cat} %'])
        writer.writerow(header)

        # Data rows
        for model_name in sorted(model_languages.keys(),
                                 key=lambda m: model_languages[m]['total_files'],
                                 reverse=True):
            data = model_languages[model_name]
            row = [model_name, data['total_files']]

            for cat in all_categories:
                count = data['categories'].get(cat, 0)
                pct = (count / data['total_files'] * 100) if data['total_files'] > 0 else 0
                row.extend([count, f"{pct:.1f}"])

            writer.writerow(row)

    print(f"✅ Generated: {csv_path_cat}")

    # Print summary
    print()
    print("=" * 80)
    print("LANGUAGE BREAKDOWN SUMMARY")
    print("=" * 80)
    print()

    # Aggregate stats
    total_files_all = sum(d['total_files'] for d in model_languages.values())
    aggregate_languages = defaultdict(int)
    aggregate_categories = defaultdict(int)

    for model_data in model_languages.values():
        for lang, count in model_data['languages'].items():
            aggregate_languages[lang] += count
        for cat, count in model_data['categories'].items():
            aggregate_categories[cat] += count

    print(f"Total files analyzed: {total_files_all:,}")
    print(f"Total models: {len(model_languages)}")
    print()

    print("Top 10 Languages (by total files):")
    sorted_langs = sorted(aggregate_languages.items(), key=lambda x: x[1], reverse=True)
    for i, (lang, count) in enumerate(sorted_langs[:10], 1):
        pct = (count / total_files_all * 100) if total_files_all > 0 else 0
        print(f"  {i:2d}. {lang:<20} {count:6,} files ({pct:5.1f}%)")

    print()
    print("By Category:")
    sorted_cats = sorted(aggregate_categories.items(), key=lambda x: x[1], reverse=True)
    for cat, count in sorted_cats:
        pct = (count / total_files_all * 100) if total_files_all > 0 else 0
        print(f"  {cat:<30} {count:6,} files ({pct:5.1f}%)")

    print()
    print("=" * 80)

if __name__ == '__main__':
    analyze_language_breakdown()
