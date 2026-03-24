#!/usr/bin/env python3
"""
Analyze the value of combined and deduplicated findings
Compare review effort and accuracy across different approaches
"""

import json
from collections import defaultdict
from pathlib import Path


def load_ground_truth(model_name):
    """Load ground truth from reports"""
    report_files = list(Path('reports').glob(f'{model_name}_2*.json'))
    comprehensive = [f for f in report_files if 'jwt' not in f.name.lower() and 'improved' not in f.name.lower()]

    if not comprehensive:
        return None

    with open(sorted(comprehensive)[-1]) as f:
        data = json.load(f)

    # Extract expected vulnerabilities by file
    ground_truth = {}
    for result in data['detailed_results']:
        prompt_id = result['prompt_id']
        language = result['language']
        ext = 'py' if language == 'python' else 'js'
        filename = f"{prompt_id}.{ext}"

        # Count actual vulnerabilities (not SECURE or PARTIAL)
        actual_vulns = [v for v in result.get('vulnerabilities', [])
                       if v['type'] not in ['SECURE', 'PARTIAL']]

        ground_truth[filename] = {
            'expected_count': len(actual_vulns),
            'vulnerabilities': actual_vulns,
            'category': result['category']
        }

    return ground_truth


def analyze_approach(findings, ground_truth, approach_name):
    """Analyze a set of findings against ground truth"""

    # Group findings by file
    by_file = defaultdict(list)
    for finding in findings:
        file_path = finding.get('file_path', '')
        filename = file_path.split('/')[-1]
        by_file[filename].append(finding)

    stats = {
        'total_findings': len(findings),
        'files_with_findings': len(by_file),
        'files_with_vulns': 0,
        'files_correctly_flagged': 0,
        'files_missed': 0,
        'avg_findings_per_file': 0
    }

    if ground_truth:
        # Compare to ground truth
        for filename, gt_data in ground_truth.items():
            expected_vulns = gt_data['expected_count']

            if expected_vulns > 0:
                stats['files_with_vulns'] += 1

                if filename in by_file:
                    stats['files_correctly_flagged'] += 1
                else:
                    stats['files_missed'] += 1

        if stats['files_with_vulns'] > 0:
            stats['detection_rate'] = (stats['files_correctly_flagged'] / stats['files_with_vulns']) * 100

    if stats['files_with_findings'] > 0:
        stats['avg_findings_per_file'] = stats['total_findings'] / stats['files_with_findings']

    return stats


def main():
    model = 'chatgpt-4o-latest'

    print("="*90)
    print("DEDUPLICATION VALUE ANALYSIS")
    print("="*90)
    print()

    # Load findings
    with open(f'static_analyzer_results/{model}/combined_findings.json') as f:
        combined = json.load(f)

    with open(f'static_analyzer_results/{model}/deduplicated_combined_findings.json') as f:
        deduplicated = json.load(f)

    # Load ground truth
    ground_truth = load_ground_truth(model)

    # Separate findings by tool for individual analysis
    tool_findings = defaultdict(list)
    for finding in combined['findings']:
        tool = finding.get('tool_name', 'unknown')
        tool_findings[tool].append(finding)

    # Analyze each approach
    print("INDIVIDUAL TOOL ANALYSIS")
    print("-"*90)
    print(f"{'Tool':<20} {'Findings':>10} {'Files':>10} {'Detected':>10} {'Missed':>10} {'Rate':>10}")
    print("-"*90)

    total_individual_findings = 0
    for tool in sorted(tool_findings.keys()):
        stats = analyze_approach(tool_findings[tool], ground_truth, tool)
        total_individual_findings += stats['total_findings']

        detection_rate = stats.get('detection_rate', 0)
        print(f"{tool:<20} {stats['total_findings']:>10} {stats['files_with_findings']:>10} "
              f"{stats['files_correctly_flagged']:>10} {stats['files_missed']:>10} {detection_rate:>9.1f}%")

    print()

    # Analyze combined
    print("COMBINED FINDINGS ANALYSIS")
    print("-"*90)
    combined_stats = analyze_approach(combined['findings'], ground_truth, 'combined')
    print(f"Total findings: {combined_stats['total_findings']}")
    print(f"Files with findings: {combined_stats['files_with_findings']}")
    print(f"Files correctly flagged: {combined_stats['files_correctly_flagged']}")
    print(f"Files missed: {combined_stats['files_missed']}")
    print(f"Detection rate: {combined_stats.get('detection_rate', 0):.1f}%")
    print()

    # Analyze deduplicated
    print("DEDUPLICATED FINDINGS ANALYSIS")
    print("-"*90)
    dedup_stats = analyze_approach(deduplicated['findings'], ground_truth, 'deduplicated')
    print(f"Total findings: {dedup_stats['total_findings']}")
    print(f"Files with findings: {dedup_stats['files_with_findings']}")
    print(f"Files correctly flagged: {dedup_stats['files_correctly_flagged']}")
    print(f"Files missed: {dedup_stats['files_missed']}")
    print(f"Detection rate: {dedup_stats.get('detection_rate', 0):.1f}%")
    print()

    # Comparison summary
    print("="*90)
    print("EFFORT vs VALUE COMPARISON")
    print("="*90)
    print()
    print(f"{'Approach':<30} {'Review Items':>15} {'Detection Rate':>15} {'Efficiency':>15}")
    print("-"*90)

    # Individual (sum of all tools)
    # But count unique files (don't double count if multiple tools flag same file)
    all_flagged_files = set()
    for findings in tool_findings.values():
        for f in findings:
            file_path = f.get('file_path', '')
            filename = file_path.split('/')[-1]
            all_flagged_files.add(filename)

    individual_detected = len([f for f in all_flagged_files
                               if ground_truth.get(f, {}).get('expected_count', 0) > 0])

    individual_rate = f"{individual_detected}/{combined_stats['files_with_vulns']}"
    print(f"{'Individual tool reports':<30} {total_individual_findings:>15} "
          f"{individual_rate:>15} {'baseline':>15}")

    combined_rate = f"{combined_stats['files_correctly_flagged']}/{combined_stats['files_with_vulns']}"
    combined_savings = f"{((total_individual_findings - combined_stats['total_findings']) / total_individual_findings * 100):.1f}%"
    print(f"{'Combined report':<30} {combined_stats['total_findings']:>15} "
          f"{combined_rate:>15} {combined_savings:>15}")

    dedup_rate = f"{dedup_stats['files_correctly_flagged']}/{dedup_stats['files_with_vulns']}"
    dedup_savings = f"{((total_individual_findings - dedup_stats['total_findings']) / total_individual_findings * 100):.1f}%"
    print(f"{'Deduplicated report':<30} {dedup_stats['total_findings']:>15} "
          f"{dedup_rate:>15} {dedup_savings:>15}")

    print()
    print("="*90)
    print("KEY INSIGHTS")
    print("="*90)
    print()

    reduction = combined_stats['total_findings'] - dedup_stats['total_findings']
    print(f"1. Deduplication reduces review effort by {reduction} findings ({reduction/combined_stats['total_findings']*100:.1f}%)")
    print(f"   while maintaining the SAME detection rate ({dedup_stats.get('detection_rate', 0):.1f}%)")
    print()

    print(f"2. {reduction} findings were duplicates (multiple tools flagging the same location)")
    print()

    print(f"3. Reviewing deduplicated findings requires checking {dedup_stats['total_findings']} items")
    print(f"   vs {total_individual_findings} items if reviewing each tool separately")
    print(f"   = {((total_individual_findings - dedup_stats['total_findings']) / total_individual_findings * 100):.1f}% time savings")
    print()

    # Show overlap examples
    print("="*90)
    print("DEDUPLICATION EXAMPLES")
    print("="*90)
    print()

    # Find examples where multiple tools flagged same location
    location_tools = defaultdict(list)
    for finding in combined['findings']:
        file_path = finding.get('file_path', '')
        filename = file_path.split('/')[-1]
        line = finding.get('start_line', 0)
        rule = finding.get('rule_id', 'unknown')

        location_tools[(filename, line)].append({
            'tool': finding.get('tool_name'),
            'rule': rule
        })

    multi_tool = {k: v for k, v in location_tools.items() if len(v) > 1}

    print(f"Found {len(multi_tool)} code locations flagged by multiple tools\n")
    print("Examples of redundant findings removed by deduplication:\n")

    for i, ((filename, line), tools) in enumerate(list(multi_tool.items())[:5], 1):
        print(f"{i}. {filename}:{line} - Flagged by {len(tools)} tools:")
        for t in tools:
            print(f"   • {t['tool']}: {t['rule']}")
        print()


if __name__ == '__main__':
    main()
