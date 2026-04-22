#!/usr/bin/env python3
"""
Generate comprehensive statistics table across all model configurations
Includes base models, temperature variants, and level variants
"""
import json
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple
import csv

def is_unsupported(result: Dict) -> bool:
    """Check if result is UNSUPPORTED (refused to generate code)"""
    vulns = result.get('vulnerabilities', [])
    for v in vulns:
        if isinstance(v, dict) and v.get('type') == 'UNSUPPORTED':
            return True
        elif 'UNSUPPORTED' in str(v):
            return True
    return False

def parse_model_name(filename: str) -> Dict:
    """Parse model name to extract base model, temperature, and level info"""
    name = filename.replace('_analysis.json', '').replace('.json', '')

    info = {
        'full_name': name,
        'base_model': name,
        'temperature': None,
        'level': None,
        'is_temp_variant': False,
        'is_level_variant': False
    }

    # Check for temperature variant
    if '_temp' in name:
        parts = name.split('_temp')
        info['base_model'] = parts[0]
        info['temperature'] = float(parts[1])
        info['is_temp_variant'] = True

    # Check for level variant
    elif '_level' in name:
        parts = name.split('_level')
        info['base_model'] = parts[0]
        info['level'] = int(parts[1])
        info['is_level_variant'] = True

    return info

def analyze_report(json_file: Path) -> Dict:
    """Analyze a single report and extract all metrics"""
    with open(json_file, 'r') as f:
        data = json.load(f)

    model_info = parse_model_name(json_file.name)
    summary = data.get('summary', {})

    # Count fully vulnerable (score = 0) and fully secure (score = max_score)
    fully_vulnerable = 0
    fully_secure = 0
    partial_secure = 0
    total_files = 0

    for result in data.get('detailed_results', []):
        if is_unsupported(result):
            continue  # Skip refused tests

        total_files += 1
        score = result.get('score', 0)
        max_score = result.get('max_score', 2)

        if score == 0:
            fully_vulnerable += 1
        elif score == max_score:
            fully_secure += 1
        else:
            partial_secure += 1

    return {
        'model_info': model_info,
        'model_name': data.get('model_name', model_info['full_name']),
        'total_prompts': summary.get('total_prompts', 0),
        'secure': summary.get('secure', 0),
        'vulnerable': summary.get('vulnerable', 0),
        'refused': summary.get('refused', 0),
        'percentage': summary.get('percentage', 0.0),
        'score': summary.get('overall_score', '0/0'),
        'fully_vulnerable': fully_vulnerable,
        'fully_secure': fully_secure,
        'partial_secure': partial_secure,
        'total_files_analyzed': total_files
    }

def categorize_model(model_name: str) -> str:
    """Categorize model as API, Local, Application, or Wrapper"""
    model_lower = model_name.lower()

    if 'codex-app' in model_lower:
        return 'Wrapper'
    elif 'claude-code' in model_lower or 'cursor' in model_lower:
        return 'Application'
    elif any(x in model_lower for x in ['deepseek', 'qwen', 'llama', 'mistral', 'codellama', 'codegemma', 'starcoder']):
        return 'Local'
    else:
        return 'API'

def main():
    reports_dir = Path('reports')

    # Find all analysis JSON files (base models only)
    all_files = list(reports_dir.glob('*_analysis.json'))

    # Exclude iteration reports, temperature variants, and level variants
    analysis_files = []
    for f in all_files:
        name = f.stem.replace('_analysis', '')
        if '_temp' not in name and '_level' not in name and 'iteration' not in name:
            analysis_files.append(f)

    if not analysis_files:
        print("No analysis files found!")
        return

    print(f"Analyzing {len(analysis_files)} model configurations...")
    print()

    # Parse all reports
    results = []
    for file in analysis_files:
        try:
            result = analyze_report(file)
            results.append(result)
        except Exception as e:
            print(f"Error analyzing {file}: {e}")

    # Since we're only analyzing base models now, all results are base models
    base_models = results
    temp_variants = []
    level_variants = []

    # Sort by percentage
    base_models.sort(key=lambda x: x['percentage'], reverse=True)

    # Calculate aggregate statistics
    print("=" * 120)
    print("COMPREHENSIVE SECURITY STATISTICS")
    print("=" * 120)
    print()

    # Overall stats
    total_configs = len(results)
    avg_security = sum(r['percentage'] for r in results) / len(results) if results else 0
    total_vulnerable_files = sum(r['fully_vulnerable'] for r in results)
    total_secure_files = sum(r['fully_secure'] for r in results)
    total_files = sum(r['total_files_analyzed'] for r in results)

    print(f"{'Metric':<50} {'Value':<30}")
    print("-" * 120)
    print(f"{'Total Configurations Analyzed':<50} {total_configs:<30}")
    print(f"{'Average Security Score Across All Configurations':<50} {avg_security:.2f}%{' ' * 20}")
    print(f"{'Total Code Samples Analyzed':<50} {total_files:<30}")
    print(f"{'Code Samples Fully Vulnerable (score = 0)':<50} {total_vulnerable_files} ({total_vulnerable_files/total_files*100:.1f}%){' ' * 10}")
    print(f"{'Code Samples Fully Secure (score = max)':<50} {total_secure_files} ({total_secure_files/total_files*100:.1f}%){' ' * 10}")
    print()

    # Best and worst configurations
    if results:
        best = max(results, key=lambda x: x['percentage'])
        worst = min(results, key=lambda x: x['percentage'])

        print(f"{'Best-Performing Configuration':<50} {best['model_name']} ({best['percentage']:.1f}%){' ' * 5}")
        print(f"{'Worst-Performing Configuration':<50} {worst['model_name']} ({worst['percentage']:.1f}%){' ' * 5}")
        print(f"{'Performance Gap (Best vs. Worst)':<50} {best['percentage'] - worst['percentage']:.1f} percentage points{' ' * 5}")
        print()

    # Base API model analysis
    if base_models:
        api_models = [r for r in base_models if categorize_model(r['model_name']) == 'API']
        if api_models:
            best_api = max(api_models, key=lambda x: x['percentage'])
            worst_api = min(api_models, key=lambda x: x['percentage'])

            print(f"{'Best Base API Model':<50} {best_api['model_name']} ({best_api['percentage']:.1f}%){' ' * 5}")
            print(f"{'Weakest Base API Model':<50} {worst_api['model_name']} ({worst_api['percentage']:.1f}%){' ' * 5}")
            print(f"{'API Model Performance Gap':<50} {best_api['percentage'] - worst_api['percentage']:.1f} percentage points{' ' * 5}")
            print()

    # Note: Temperature and level variants are excluded from baseline analysis
    print(f"{'Analysis Scope':<50} {'Base models only (no temp/level variants)':<30}")
    print()

    # Language distribution (count files from output directories)
    all_files = set()
    extension_counts = defaultdict(int)

    # Count files from the output directories for base models
    output_dir = Path('output')
    for result in base_models:  # Only base models to avoid duplicate counting
        model_dir = output_dir / result['model_info']['base_model']
        if model_dir.exists():
            for file_path in model_dir.glob('*'):
                if file_path.is_file():
                    all_files.add(file_path.name)
                    if '.' in file_path.name:
                        ext = file_path.suffix.lstrip('.')
                        extension_counts[ext] += 1

    if all_files:
        total_unique_files = len(all_files)
        num_languages = len(extension_counts)
        languages_list = ', '.join(sorted(extension_counts.keys()))
        print(f"{'Multi-Language Files Analyzed':<50} {total_unique_files} unique test files")
        print(f"{'Languages Covered':<50} {num_languages} languages: {languages_list}")
    print()

    # Detailed breakdown by category
    print("=" * 120)
    print("DETAILED BREAKDOWN BY MODEL CATEGORY")
    print("=" * 120)
    print()

    # Group by category
    by_category = defaultdict(list)
    for r in base_models:
        category = categorize_model(r['model_name'])
        by_category[category].append(r)

    for category in ['Wrapper', 'Application', 'API', 'Local']:
        models = by_category.get(category, [])
        if not models:
            continue

        print(f"{category} Models ({len(models)}):")
        print(f"  {'Model':<40} {'Score':<15} {'% Secure':<12} {'Fully Vuln':<12} {'Fully Secure':<15}")
        print("  " + "-" * 110)

        for r in sorted(models, key=lambda x: x['percentage'], reverse=True):
            print(f"  {r['model_name']:<40} {r['score']:<15} {r['percentage']:>6.1f}%      "
                  f"{r['fully_vulnerable']:<12} {r['fully_secure']:<15}")

        avg = sum(m['percentage'] for m in models) / len(models)
        print(f"  {'Average':<40} {'':<15} {avg:>6.1f}%")
        print()

    # Export comprehensive CSV
    csv_file = reports_dir / 'comprehensive_statistics.csv'
    with open(csv_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'Model', 'Category', 'Base Model', 'Temperature', 'Level',
            'Score', 'Percent Secure', 'Total Prompts', 'Secure', 'Vulnerable', 'Refused',
            'Fully Vulnerable', 'Fully Secure', 'Partial Secure'
        ])
        writer.writeheader()

        for result in sorted(results, key=lambda x: x['percentage'], reverse=True):
            info = result['model_info']
            writer.writerow({
                'Model': result['model_name'],
                'Category': categorize_model(result['model_name']),
                'Base Model': info['base_model'],
                'Temperature': info['temperature'] if info['temperature'] is not None else '',
                'Level': info['level'] if info['level'] is not None else '',
                'Score': result['score'],
                'Percent Secure': f"{result['percentage']:.1f}%",
                'Total Prompts': result['total_prompts'],
                'Secure': result['secure'],
                'Vulnerable': result['vulnerable'],
                'Refused': result['refused'],
                'Fully Vulnerable': result['fully_vulnerable'],
                'Fully Secure': result['fully_secure'],
                'Partial Secure': result['partial_secure']
            })

    print(f"✅ Comprehensive CSV exported to: {csv_file}")
    print()

    # Key insights
    print("=" * 120)
    print("KEY INSIGHTS")
    print("=" * 120)
    print()

    # Note: Temperature and level analysis excluded from baseline reports
    print(f"1. Baseline Model Analysis Only:")
    print(f"   - Excluding temperature variants and prompt level studies")
    print(f"   - {len(base_models)} baseline models analyzed")
    print()

    # Vulnerability concentration
    vuln_rate = total_vulnerable_files / total_files * 100 if total_files > 0 else 0
    secure_rate = total_secure_files / total_files * 100 if total_files > 0 else 0

    print(f"2. Vulnerability Distribution:")
    print(f"   - {vuln_rate:.1f}% of code samples are fully vulnerable (0 points)")
    print(f"   - {secure_rate:.1f}% of code samples are fully secure (maximum points)")
    print(f"   - {100 - vuln_rate - secure_rate:.1f}% are partially secure (partial points)")
    print()

if __name__ == '__main__':
    main()
