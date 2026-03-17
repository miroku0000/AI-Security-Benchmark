#!/usr/bin/env python3
"""
Analyze SAST tool findings to show both raw counts and deduplicated counts
"""

import json
from pathlib import Path
from collections import defaultdict

def analyze_tool_findings(model_name):
    """Analyze findings from all SAST tools"""

    results_dir = Path('static_analyzer_results') / model_name / 'normalized'

    tool_analysis = {}

    # Process each tool's findings
    for json_file in results_dir.glob('*.json'):
        # Extract tool name from filename
        filename = json_file.stem
        if 'bandit' in filename:
            tool_name = 'bandit'
        elif 'semgrep' in filename or 'opengrep' in filename:
            tool_name = 'semgrep' if 'semgrep' in filename else 'opengrep'
        elif 'normalized' in filename:
            tool_name = 'normalized'
        elif 'gositter' in filename:
            tool_name = 'gositter'
        elif 'bearer' in filename:
            tool_name = 'bearer'
        else:
            continue  # Skip other tools

        with open(json_file) as f:
            data = json.load(f)

        findings = data.get('findings', [])

        # Count raw findings
        raw_count = len(findings)

        # Group by (file, rule_id) for unique issues
        unique_issues = defaultdict(list)
        for finding in findings:
            file_path = finding.get('file_path', '')
            filename = file_path.split('/')[-1] if file_path else 'unknown'
            rule_id = finding.get('rule_id', 'UNKNOWN')

            unique_issues[(filename, rule_id)].append(finding)

        # Store analysis
        tool_analysis[tool_name] = {
            'raw_findings': raw_count,
            'unique_issues': len(unique_issues),
            'grouped_issues': unique_issues
        }

    return tool_analysis


def print_comparison(model_name):
    """Print comparison table"""

    tool_analysis = analyze_tool_findings(model_name)

    # Load accuracy results
    accuracy_file = f'sast_accuracy_{model_name}_20260208_094200.json'
    with open(accuracy_file) as f:
        accuracy_data = json.load(f)

    # Aggregate accuracy metrics
    tool_accuracy = defaultdict(lambda: {'tp': 0, 'fp': 0, 'fn': 0})
    for file_result in accuracy_data['file_results']:
        for tool, metrics in file_result['tool_results'].items():
            tool_accuracy[tool]['tp'] += metrics['true_positives']
            tool_accuracy[tool]['fp'] += metrics['false_positives']
            tool_accuracy[tool]['fn'] += metrics['false_negatives']

    print("="*100)
    print(f"SAST TOOL FINDINGS COMPARISON - {model_name}")
    print("="*100)
    print()
    print(f"{'Tool':<15} {'Raw Findings':>15} {'Unique Issues':>15} {'Instances/Issue':>18} {'TP':>6} {'FP':>6} {'FN':>6}")
    print("-"*100)

    for tool in sorted(tool_analysis.keys()):
        analysis = tool_analysis[tool]
        accuracy = tool_accuracy.get(tool, {})

        raw = analysis['raw_findings']
        unique = analysis['unique_issues']
        avg_instances = raw / unique if unique > 0 else 0

        tp = accuracy.get('tp', 0)
        fp = accuracy.get('fp', 0)
        fn = accuracy.get('fn', 0)

        print(f"{tool:<15} {raw:>15} {unique:>15} {avg_instances:>17.1f}x {tp:>6} {fp:>6} {fn:>6}")

    print()
    print("="*100)
    print("EXPLANATION:")
    print("- Raw Findings: Total number of findings reported by the tool")
    print("- Unique Issues: Number of distinct (file, rule) combinations")
    print("- Instances/Issue: Average number of instances per unique issue (shows if tool reports duplicates)")
    print("- TP/FP/FN: True Positives, False Positives, False Negatives from accuracy analysis")
    print()
    print("NOTE: A higher 'Instances/Issue' ratio means the tool reports the same issue multiple")
    print("      times in the same file (e.g., normalized tool reports CWE-312 at 3 different lines)")
    print("="*100)

    # Show detailed breakdown for normalized tool
    if 'normalized' in tool_analysis:
        print()
        print("NORMALIZED TOOL - DETAILED BREAKDOWN:")
        print("-"*100)
        for (filename, rule_id), instances in sorted(tool_analysis['normalized']['grouped_issues'].items()):
            if len(instances) > 1:
                lines = [str(f.get('start_line', '?')) for f in instances]
                print(f"  {filename} - {rule_id}: {len(instances)} instances at lines {', '.join(lines)}")


if __name__ == '__main__':
    print_comparison('chatgpt-4o-latest')
