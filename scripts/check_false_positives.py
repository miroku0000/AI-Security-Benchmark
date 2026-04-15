#!/usr/bin/env python3
"""
Check for false positives and false negatives in top vulnerable categories
Samples actual code files and provides manual review guidance
"""

import json
import glob
import os
import random
from collections import defaultdict

# Top 10 most vulnerable categories to check
TOP_CATEGORIES = [
    'prometheus_metrics_exposed',
    'weak_biometric_auth',
    'ml_unsafe_deserialization',
    'postgres_sql_injection',
    'ml_adversarial_examples',
    'ats_bypass',
    'missing_ssl_pinning',
    'graphql_security',
    'container_security',
    'buffer_overflow'
]

def find_test_files_by_category(category):
    """Find which test IDs correspond to a category"""
    # Load prompts to map test IDs to categories
    prompt_files = glob.glob('prompts/*.yaml') + glob.glob('prompts/*.json')
    test_mapping = {}

    for prompt_file in prompt_files:
        try:
            import yaml
            with open(prompt_file) as f:
                prompts = yaml.safe_load(f)
                if isinstance(prompts, list):
                    for prompt in prompts:
                        if prompt.get('category') == category:
                            test_mapping[prompt.get('id')] = prompt.get('description', '')
        except:
            pass

    return test_mapping

def collect_samples(category, max_samples=5):
    """Collect sample files for a category from multiple models"""
    samples = {'vulnerable': [], 'secure': []}

    # Sample from different quality tiers
    priority_models = [
        'codex-app-security-skill',  # Best model
        'claude-sonnet-4-5',          # Good model
        'deepseek-coder',             # Mid-tier model
        'codellama'                   # Lower-tier model
    ]

    for model in priority_models:
        output_dir = f'output/{model}'
        if not os.path.isdir(output_dir):
            continue

        # Try to find files matching the category pattern
        # Most categories map to test file prefixes
        category_prefix = category.replace('_', '_')

        for file in glob.glob(f'{output_dir}/*'):
            if len(samples['vulnerable']) >= max_samples and len(samples['secure']) >= max_samples:
                break

            filename = os.path.basename(file)

            # Check if file relates to this category (heuristic)
            if any(prefix in filename.lower() for prefix in [
                category.split('_')[0],  # First word of category
                category.split('_')[-1] if '_' in category else category  # Last word
            ]):
                # Read file and detect
                try:
                    with open(file, 'r') as f:
                        code = f.read()

                    # Run detector on it
                    from runner import detect_vulnerabilities
                    status = detect_vulnerabilities(code, filename)

                    if status == 'VULNERABLE' and len(samples['vulnerable']) < max_samples:
                        samples['vulnerable'].append({
                            'model': model,
                            'file': file,
                            'code_preview': code[:500]
                        })
                    elif status == 'SECURE' and len(samples['secure']) < max_samples:
                        samples['secure'].append({
                            'model': model,
                            'file': file,
                            'code_preview': code[:500]
                        })
                except:
                    pass

    return samples

def main():
    print("=" * 80)
    print("FALSE POSITIVE/NEGATIVE CHECKER")
    print("=" * 80)
    print()
    print("This script examines actual code samples from the top vulnerable categories")
    print("to identify potential false positives and false negatives.")
    print()

    results = []

    for category in TOP_CATEGORIES:
        print(f"\n{'='*80}")
        print(f"Category: {category}")
        print(f"{'='*80}")

        # Get statistics from aggregated results
        vuln_count = 0
        secure_count = 0
        total_count = 0

        for report_file in glob.glob('reports/*_analysis.json')[:10]:
            try:
                with open(report_file) as f:
                    data = json.load(f)
                    if 'categories' in data and category in data['categories']:
                        stats = data['categories'][category]
                        vuln_count += stats.get('vulnerable', 0)
                        secure_count += stats.get('secure', 0)
                        total_count += stats.get('total', 0)
            except:
                continue

        vuln_rate = (vuln_count / total_count * 100) if total_count > 0 else 0

        print(f"Vulnerability Rate: {vuln_rate:.1f}% ({vuln_count}/{total_count})")
        print(f"Secure Rate: {(secure_count/total_count*100) if total_count > 0 else 0:.1f}% ({secure_count}/{total_count})")
        print()

        # Find sample files
        print("Sample files to manually review:")
        print()

        # Look for files in a few models
        for model in ['codex-app-security-skill', 'deepseek-coder', 'codellama']:
            output_dir = f'output/{model}'
            if os.path.isdir(output_dir):
                # Find potential files (heuristic based on category name)
                category_keywords = category.lower().split('_')
                files = []
                for file in os.listdir(output_dir):
                    if any(kw in file.lower() for kw in category_keywords[:2]):  # First 2 keywords
                        files.append(file)

                if files:
                    print(f"  {model}:")
                    for f in files[:3]:  # Show max 3 files
                        print(f"    - {output_dir}/{f}")
                    break  # Only show one model's examples

        print()
        print(f"MANUAL REVIEW NEEDED:")
        print(f"  1. Check if VULNERABLE verdicts are correct (no false positives)")
        print(f"  2. Check if SECURE verdicts are correct (no false negatives)")
        print(f"  3. Verify detector logic in tests/test_{category}.py")
        print()

        results.append({
            'category': category,
            'vuln_rate': vuln_rate,
            'vuln_count': vuln_count,
            'secure_count': secure_count,
            'total_count': total_count
        })

    print("\n" + "=" * 80)
    print("SUMMARY - PRIORITY REVIEW ORDER")
    print("=" * 80)
    print()
    print("Categories with >70% vulnerability rate need immediate review:")
    print()

    for r in sorted(results, key=lambda x: x['vuln_rate'], reverse=True):
        if r['vuln_rate'] > 70:
            print(f"⚠️  {r['category']}: {r['vuln_rate']:.1f}% vulnerable")
            print(f"    -> Review test detector in tests/test_{r['category']}.py")
            print(f"    -> Sample files in output/*/{{keyword matching {r['category'].split('_')[0]}}}*")
            print()

if __name__ == '__main__':
    main()
