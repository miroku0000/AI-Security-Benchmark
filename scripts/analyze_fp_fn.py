#!/usr/bin/env python3
"""
Analyze all completed reports for false positives and false negatives.
"""
import json
from pathlib import Path
from collections import defaultdict

def analyze_reports():
    """Analyze all completed reports for FP/FN patterns."""

    reports_dir = Path("reports")
    report_files = sorted(reports_dir.glob("*_20260321*.json"))

    print(f"Analyzing {len(report_files)} completed reports...\n")

    # Track patterns across all models
    fp_candidates = defaultdict(list)  # Potential false positives
    fn_candidates = defaultdict(list)  # Potential false negatives

    # Suspicious patterns that might indicate detector issues
    suspicious_patterns = {
        'buffer_overflow': [],
        'format_string': [],
        'all_categories': defaultdict(lambda: {'secure': 0, 'vulnerable': 0, 'total': 0})
    }

    for report_file in report_files:
        try:
            with open(report_file) as f:
                data = json.load(f)

            model_name = data.get('model_name', 'Unknown')
            results = data.get('detailed_results', [])

            for result in results:
                prompt_id = result.get('prompt_id', '')
                category = result.get('category', '')
                language = result.get('language', '')
                score = result.get('score', 0)
                max_score = result.get('max_score', 2)
                vulns = result.get('vulnerabilities', [])

                # Track by category
                suspicious_patterns['all_categories'][category]['total'] += 1
                if score == max_score:
                    suspicious_patterns['all_categories'][category]['secure'] += 1
                elif score == 0:
                    suspicious_patterns['all_categories'][category]['vulnerable'] += 1

                # Check for buffer overflow issues (cpp/c files)
                if category == 'buffer_overflow' and language in ['cpp', 'c']:
                    for vuln in vulns:
                        desc = vuln.get('description', '')

                        # Check for potential false positives
                        # FP: Flagging fgets as gets, strncpy as strcpy, etc.
                        if 'gets()' in desc:
                            # Check if it might actually be fgets
                            suspicious_patterns['buffer_overflow'].append({
                                'model': model_name,
                                'prompt_id': prompt_id,
                                'issue': 'Possible FP: gets() detection',
                                'description': desc,
                                'score': f"{score}/{max_score}"
                            })

                        if 'strcpy()' in desc and score == 0:
                            suspicious_patterns['buffer_overflow'].append({
                                'model': model_name,
                                'prompt_id': prompt_id,
                                'issue': 'strcpy detected',
                                'description': desc,
                                'score': f"{score}/{max_score}"
                            })

                # Check for format string issues
                if category == 'format_string' and language in ['cpp', 'c']:
                    for vuln in vulns:
                        suspicious_patterns['format_string'].append({
                            'model': model_name,
                            'prompt_id': prompt_id,
                            'type': vuln.get('type', ''),
                            'severity': vuln.get('severity', ''),
                            'description': vuln.get('description', ''),
                            'score': f"{score}/{max_score}"
                        })

        except Exception as e:
            print(f"Error processing {report_file}: {e}")
            continue

    # Print findings
    print("=" * 80)
    print("FALSE POSITIVE/NEGATIVE ANALYSIS")
    print("=" * 80)
    print()

    # Buffer overflow findings
    print("### BUFFER OVERFLOW DETECTOR ANALYSIS ###")
    print()
    if suspicious_patterns['buffer_overflow']:
        print(f"Found {len(suspicious_patterns['buffer_overflow'])} potential issues:")
        print()

        # Group by issue type
        by_issue = defaultdict(list)
        for item in suspicious_patterns['buffer_overflow']:
            by_issue[item['issue']].append(item)

        for issue_type, items in by_issue.items():
            print(f"\n{issue_type}: {len(items)} occurrences")
            # Show first 3 examples
            for item in items[:3]:
                print(f"  - {item['model']}/{item['prompt_id']}: {item['description'][:80]}...")
    else:
        print("✓ No suspicious buffer overflow patterns detected")

    print()
    print("=" * 80)

    # Format string findings
    print("\n### FORMAT STRING DETECTOR ANALYSIS ###")
    print()
    if suspicious_patterns['format_string']:
        print(f"Analyzed {len(suspicious_patterns['format_string'])} format string tests:")
        print()

        # Count by result type
        secure_count = sum(1 for x in suspicious_patterns['format_string'] if '2/2' in x['score'])
        vuln_count = sum(1 for x in suspicious_patterns['format_string'] if '0/2' in x['score'])
        partial_count = len(suspicious_patterns['format_string']) - secure_count - vuln_count

        print(f"  Secure: {secure_count}")
        print(f"  Partial: {partial_count}")
        print(f"  Vulnerable: {vuln_count}")

        # Show some examples
        print("\nExamples:")
        for item in suspicious_patterns['format_string'][:5]:
            print(f"  {item['model']}/{item['prompt_id']} [{item['score']}]: {item['description'][:60]}...")
    else:
        print("No format string tests found")

    print()
    print("=" * 80)

    # Category-wide analysis
    print("\n### CATEGORY-WIDE PATTERNS ###")
    print()
    for category, stats in sorted(suspicious_patterns['all_categories'].items()):
        if stats['total'] > 0:
            secure_pct = stats['secure'] / stats['total'] * 100
            vuln_pct = stats['vulnerable'] / stats['total'] * 100

            print(f"{category:30s} {stats['total']:3d} tests | "
                  f"Secure: {stats['secure']:3d} ({secure_pct:5.1f}%) | "
                  f"Vuln: {stats['vulnerable']:3d} ({vuln_pct:5.1f}%)")

    print()
    print("=" * 80)

    return suspicious_patterns

if __name__ == '__main__':
    analyze_reports()
