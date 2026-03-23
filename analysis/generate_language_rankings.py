#!/usr/bin/env python3
"""
Generate per-language security rankings for all benchmarked AI models.

This script analyzes all JSON reports and creates language-specific rankings
showing which models perform best for each programming language.
"""

import json
import os
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple

# Language mappings based on file extensions and prompt patterns
LANGUAGE_MAPPINGS = {
    'python': {
        'extensions': ['.py'],
        'categories': ['sql_injection', 'xss', 'path_traversal', 'command_injection',
                      'hardcoded_secrets', 'insecure_deserialization', 'xxe', 'ssrf',
                      'insecure_crypto', 'insecure_auth', 'business_logic']
    },
    'javascript': {
        'extensions': ['.js'],
        'categories': ['xss', 'command_injection', 'path_traversal', 'insecure_crypto',
                      'hardcoded_secrets', 'insecure_auth']
    },
    'java': {
        'extensions': ['.java'],
        'categories': ['sql_injection', 'xss', 'command_injection', 'insecure_deserialization',
                      'xxe', 'hardcoded_secrets', 'insecure_crypto']
    },
    'csharp': {
        'extensions': ['.cs'],
        'categories': ['sql_injection', 'xss', 'command_injection', 'insecure_deserialization',
                      'hardcoded_secrets', 'insecure_crypto']
    },
    'c_cpp': {
        'extensions': ['.c', '.cpp'],
        'categories': ['buffer_overflow', 'format_string', 'command_injection',
                      'hardcoded_secrets', 'insecure_crypto']
    },
    'go': {
        'extensions': ['.go'],
        'categories': ['sql_injection', 'command_injection', 'path_traversal',
                      'hardcoded_secrets', 'insecure_crypto']
    },
    'rust': {
        'extensions': ['.rs'],
        'categories': ['sql_injection', 'command_injection', 'insecure_crypto',
                      'hardcoded_secrets']
    }
}


def load_report(report_path: str) -> Dict:
    """Load a single JSON report."""
    with open(report_path, 'r') as f:
        return json.load(f)


def determine_language(filename: str, category: str) -> str:
    """Determine the programming language from filename and category."""
    ext = Path(filename).suffix.lower()

    # Direct extension mapping
    for lang, config in LANGUAGE_MAPPINGS.items():
        if ext in config['extensions']:
            return lang

    # Special cases based on category
    if category in ['buffer_overflow', 'format_string']:
        return 'c_cpp'

    # Default to python for unknown
    return 'python'


def calculate_language_scores(report_path: str) -> Dict[str, Dict]:
    """Calculate scores per language for a single model."""
    report = load_report(report_path)
    model_name = report.get('model_name', 'unknown')

    language_stats = defaultdict(lambda: {'score': 0, 'max_score': 0, 'tests': []})

    # Get results from detailed_results (it's a list in the new format)
    detailed_results = report.get('detailed_results', [])

    # Iterate through all test results
    for result in detailed_results:
        prompt_id = result.get('prompt_id', '')
        category = result.get('category', '')
        language = result.get('language', 'python')  # Language is directly available
        score = result.get('score', 0)
        max_score = result.get('max_score', 2)

        # Use language from report directly
        lang = language if language else 'python'

        # Accumulate stats
        language_stats[lang]['score'] += score
        language_stats[lang]['max_score'] += max_score
        language_stats[lang]['tests'].append({
            'prompt_id': prompt_id,
            'category': category,
            'score': score,
            'max_score': max_score
        })

    # Calculate percentages
    for lang in language_stats:
        total_score = language_stats[lang]['score']
        max_score = language_stats[lang]['max_score']
        language_stats[lang]['percentage'] = (total_score / max_score * 100) if max_score > 0 else 0
        language_stats[lang]['model'] = model_name

    return dict(language_stats)


def generate_rankings(reports_dir: str = 'reports') -> Dict[str, List[Tuple]]:
    """Generate rankings for all languages across all models."""
    language_rankings = defaultdict(list)

    # Find all report files
    report_files = list(Path(reports_dir).glob('*_208point_20260321.json'))

    print(f"Found {len(report_files)} reports to analyze")

    for report_path in report_files:
        model_scores = calculate_language_scores(str(report_path))

        # Add to rankings
        for lang, stats in model_scores.items():
            language_rankings[lang].append({
                'model': stats['model'],
                'score': stats['score'],
                'max_score': stats['max_score'],
                'percentage': stats['percentage'],
                'test_count': len(stats['tests'])
            })

    # Sort each language ranking by percentage (descending)
    for lang in language_rankings:
        language_rankings[lang].sort(key=lambda x: x['percentage'], reverse=True)

    return dict(language_rankings)


def format_rankings_markdown(rankings: Dict[str, List]) -> str:
    """Format rankings as markdown tables."""
    md = "# AI Model Security Rankings by Programming Language\n\n"
    md += "Generated from AI Security Benchmark results (March 2026)\n\n"
    md += "---\n\n"

    language_names = {
        'python': 'Python',
        'javascript': 'JavaScript',
        'java': 'Java',
        'csharp': 'C#',
        'c_cpp': 'C/C++',
        'go': 'Go',
        'rust': 'Rust'
    }

    for lang_key in ['python', 'javascript', 'java', 'csharp', 'c_cpp', 'go', 'rust']:
        if lang_key not in rankings:
            continue

        lang_name = language_names.get(lang_key, lang_key)
        lang_data = rankings[lang_key]

        md += f"## {lang_name}\n\n"
        md += f"**{len(lang_data)} models tested** | "
        md += f"**{lang_data[0]['test_count']} security tests** per model\n\n"

        # Table header
        md += "| Rank | Model | Security Score | Tests Passed | Percentage |\n"
        md += "|------|-------|----------------|--------------|------------|\n"

        # Top 10 models
        for i, model in enumerate(lang_data[:10], 1):
            model_name = model['model']
            score = model['score']
            max_score = model['max_score']
            pct = model['percentage']

            md += f"| {i} | **{model_name}** | {score}/{max_score} | {score//2}/{max_score//2} | {pct:.1f}% |\n"

        # Summary stats
        avg_pct = sum(m['percentage'] for m in lang_data) / len(lang_data)
        md += f"\n**Average security score**: {avg_pct:.1f}%\n\n"

        # Top 3 highlight
        if len(lang_data) >= 3:
            md += f"**Best models for {lang_name}**:\n"
            for i in range(min(3, len(lang_data))):
                m = lang_data[i]
                md += f"{i+1}. {m['model']} ({m['percentage']:.1f}%)\n"

        md += "\n---\n\n"

    return md


def generate_json_export(rankings: Dict[str, List]) -> Dict:
    """Generate JSON export for the recommendation wizard."""
    export = {
        'metadata': {
            'generated': '2026-03-21',
            'version': '1.0',
            'description': 'Per-language AI model security rankings'
        },
        'languages': {}
    }

    language_names = {
        'python': 'Python',
        'javascript': 'JavaScript',
        'java': 'Java',
        'csharp': 'C#',
        'c_cpp': 'C/C++',
        'go': 'Go',
        'rust': 'Rust'
    }

    for lang_key, lang_data in rankings.items():
        lang_name = language_names.get(lang_key, lang_key)

        export['languages'][lang_key] = {
            'name': lang_name,
            'models': [
                {
                    'model': m['model'],
                    'score': m['score'],
                    'max_score': m['max_score'],
                    'percentage': round(m['percentage'], 1),
                    'rank': i + 1
                }
                for i, m in enumerate(lang_data)
            ],
            'top_3': [m['model'] for m in lang_data[:3]],
            'average_score': round(sum(m['percentage'] for m in lang_data) / len(lang_data), 1)
        }

    return export


def main():
    """Main execution."""
    print("=" * 60)
    print("AI Security Benchmark - Language-Specific Rankings")
    print("=" * 60)
    print()

    # Generate rankings
    print("Analyzing benchmark reports...")
    rankings = generate_rankings()

    print(f"✓ Analyzed {sum(len(v) for v in rankings.values())} model-language combinations")
    print(f"✓ Languages covered: {len(rankings)}")
    print()

    # Create output directory
    output_dir = Path('analysis')
    output_dir.mkdir(exist_ok=True)

    # Generate markdown report
    print("Generating markdown report...")
    md_content = format_rankings_markdown(rankings)
    md_path = output_dir / 'language_rankings.md'
    with open(md_path, 'w') as f:
        f.write(md_content)
    print(f"✓ Saved: {md_path}")

    # Generate JSON export
    print("Generating JSON export...")
    json_data = generate_json_export(rankings)
    json_path = output_dir / 'language_rankings.json'
    with open(json_path, 'w') as f:
        json.dump(json_data, f, indent=2)
    print(f"✓ Saved: {json_path}")

    print()
    print("=" * 60)
    print("Summary by Language:")
    print("=" * 60)

    language_names = {
        'python': 'Python',
        'javascript': 'JavaScript',
        'java': 'Java',
        'csharp': 'C#',
        'c_cpp': 'C/C++',
        'go': 'Go',
        'rust': 'Rust'
    }

    for lang_key in ['python', 'javascript', 'java', 'csharp', 'c_cpp', 'go', 'rust']:
        if lang_key not in rankings:
            continue

        lang_name = language_names.get(lang_key, lang_key)
        top_model = rankings[lang_key][0]

        print(f"\n{lang_name}:")
        print(f"  Top Model: {top_model['model']} ({top_model['percentage']:.1f}%)")
        print(f"  Models Tested: {len(rankings[lang_key])}")
        print(f"  Average Score: {sum(m['percentage'] for m in rankings[lang_key]) / len(rankings[lang_key]):.1f}%")

    print()
    print("=" * 60)
    print("✓ Language rankings generated successfully!")
    print("=" * 60)


if __name__ == '__main__':
    main()
