#!/usr/bin/env python3
"""
Generate CSV summary report from JSON analysis files
"""

import json
import os
import csv
from pathlib import Path
from typing import Dict, List, Tuple

def parse_report(json_file: Path) -> Dict:
    """Parse a JSON report and extract key metrics."""
    with open(json_file, 'r') as f:
        data = json.load(f)

    # Extract metrics from summary section
    summary = data.get('summary', {})
    model_name = summary.get('model', json_file.stem)

    # Parse overall_score which is in format "980/1522"
    # Note: After UNSUPPORTED fix, this score already excludes refused tests
    overall_score = summary.get('overall_score', '0/0')
    if '/' in overall_score:
        score, max_score = overall_score.split('/')
        score = int(score)
        max_score = int(max_score)
    else:
        score = 0
        max_score = 0

    # Get percentage directly from summary (excludes refused tests)
    percentage = summary.get('percentage', 0.0)

    # Get secure/vulnerable counts (excludes refused tests)
    secure = summary.get('secure', 0)
    vulnerable = summary.get('vulnerable', 0)
    refused = summary.get('refused', 0)
    total_prompts = summary.get('total_prompts', 0)

    # Calculate percent refused (failed to write code)
    percent_refused = (refused / total_prompts * 100) if total_prompts > 0 else 0.0

    return {
        'model': model_name,
        'score': score,
        'max_score': max_score,
        'percentage': percentage,
        'percent_refused': percent_refused,
        'secure': secure,
        'vulnerable': vulnerable,
        'refused': refused,
        'total_prompts': total_prompts
    }

def determine_provider(model_name: str) -> str:
    """Determine the provider based on model name."""
    model_lower = model_name.lower()

    if 'codex-app' in model_lower:
        return 'OpenAI'
    elif 'cursor' in model_lower:
        return 'Anysphere'
    elif 'gpt' in model_lower or 'o1' in model_lower or 'o3' in model_lower:
        return 'OpenAI'
    elif 'claude' in model_lower:
        return 'Anthropic'
    elif 'gemini' in model_lower:
        return 'Google'
    elif any(x in model_lower for x in ['deepseek', 'qwen', 'llama', 'mistral', 'codellama', 'codegemma', 'starcoder']):
        return 'Ollama'
    else:
        return 'Unknown'

def determine_type(model_name: str) -> str:
    """Determine the type based on model name."""
    model_lower = model_name.lower()

    if 'codex-app' in model_lower:
        return 'Wrapper (GPT-5.4)'
    elif 'claude-code' in model_lower or 'cursor' in model_lower:
        return 'Application'
    elif any(x in model_lower for x in ['deepseek', 'qwen', 'llama', 'mistral', 'codellama', 'codegemma', 'starcoder']):
        return 'Local'
    else:
        return 'API'

def main():
    """Main function to generate CSV summary."""
    reports_dir = Path('reports')

    # Find all JSON report files for base models (not temp/level variants)
    analysis_files = []
    for file in reports_dir.glob('*.json'):
        # Skip non-report files
        if file.name in ['model_security_rankings.json', 'schema.json']:
            continue
        name = file.stem
        # Skip temperature and level variants
        if '_temp' not in name and '_level' not in name and 'iteration' not in name:
            analysis_files.append(file)

    print(f"Found {len(analysis_files)} base model reports")

    # Parse all reports
    results = []
    for file in analysis_files:
        try:
            result = parse_report(file)
            result['provider'] = determine_provider(result['model'])
            result['type'] = determine_type(result['model'])
            results.append(result)
            print(f"✓ Parsed {result['model']}: {result['score']}/{result['max_score']} ({result['percentage']:.1f}%)")
        except Exception as e:
            print(f"✗ Error parsing {file}: {e}")

    # Sort by score (descending)
    results.sort(key=lambda x: (x['score'], x['percentage']), reverse=True)

    # Add rank
    for i, result in enumerate(results, 1):
        result['rank'] = i

    # Write CSV
    csv_file = 'reports/model_security_rankings.csv'
    with open(csv_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'Rank', 'Model/Application', 'Score', 'Percent Secure', 'Percent Failed to Write Code', 'Provider', 'Type'
        ])
        writer.writeheader()

        for result in results:
            writer.writerow({
                'Rank': result['rank'],
                'Model/Application': result['model'],
                'Score': f"{result['score']}/{result['max_score']}",
                'Percent Secure': f"{result['percentage']:.1f}%",
                'Percent Failed to Write Code': f"{result['percent_refused']:.1f}%",
                'Provider': result['provider'],
                'Type': result['type']
            })

    print(f"\n✅ CSV report generated: {csv_file}")
    print(f"\nTop 10 Models:")
    print(f"{'Rank':<6} {'Model/Application':<40} {'Score':<15} {'% Secure':<12} {'% Refused':<12} {'Provider':<15} {'Type':<20}")
    print("=" * 125)

    for result in results[:10]:
        print(f"{result['rank']:<6} {result['model']:<40} {result['score']}/{result['max_score']:<12} "
              f"{result['percentage']:>6.1f}%      {result['percent_refused']:>6.1f}%      {result['provider']:<15} {result['type']:<20}")

    # Also create a formatted markdown table
    md_file = 'reports/model_security_rankings.md'
    with open(md_file, 'w') as f:
        f.write("# AI Model Security Benchmark Results\n\n")
        f.write(f"Total Models Tested: {len(results)}\n\n")
        f.write("## Rankings\n\n")
        f.write("| Rank | Model/Application | Score | Percent Secure | Percent Failed to Write Code | Provider | Type |\n")
        f.write("|------|-------------------|-------|----------------|------------------------------|----------|------|\n")

        for result in results:
            f.write(f"| {result['rank']} | {result['model']} | {result['score']}/{result['max_score']} | "
                   f"{result['percentage']:.1f}% | {result['percent_refused']:.1f}% | {result['provider']} | {result['type']} |\n")

    print(f"✅ Markdown report generated: {md_file}\n")

if __name__ == '__main__':
    main()
