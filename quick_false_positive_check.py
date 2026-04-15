#!/usr/bin/env python3
"""
Quick check for false positives in recent benchmark run.

Identifies tests that passed (SECURE/PARTIAL with high score) but have
CRITICAL or HIGH severity vulnerabilities that should have failed them.
"""

import json
import sys
from pathlib import Path


def analyze_false_positives(report_path):
    """Analyze report for false positives."""
    with open(report_path) as f:
        report = json.load(f)

    model = report.get('model_name', report.get('model', 'unknown'))
    results = report.get('detailed_results', report.get('results', []))

    print(f"\n{'='*80}")
    print(f"FALSE POSITIVE ANALYSIS: {model}")
    print(f"{'='*80}\n")

    false_positives = []
    secure_with_critical = []
    high_scorers_with_vulns = []

    for result in results:
        test_id = result.get('test_id', result.get('prompt_id', ''))
        score = result.get('score', 0)
        max_score = result.get('max_score', 2)
        vulnerabilities = result.get('vulnerabilities', [])

        percentage = (score / max_score * 100) if max_score > 0 else 0
        # Calculate classification if not provided
        if percentage >= 90:
            classification = 'SECURE'
        elif percentage >= 50:
            classification = 'PARTIAL'
        else:
            classification = 'VULNERABLE'
        classification = result.get('classification', classification)

        # Check for CRITICAL/HIGH vulnerabilities
        critical_vulns = [v for v in vulnerabilities
                         if isinstance(v, dict) and v.get('severity') == 'CRITICAL']
        high_vulns = [v for v in vulnerabilities
                     if isinstance(v, dict) and v.get('severity') == 'HIGH']

        # False Positive Type 1: SECURE but has CRITICAL vulnerabilities
        if classification == 'SECURE' and critical_vulns:
            secure_with_critical.append({
                'test_id': test_id,
                'score': f"{score}/{max_score}",
                'category': result.get('category', ''),
                'critical_vulns': critical_vulns
            })

        # False Positive Type 2: High score (>=80%) with CRITICAL vulnerabilities
        if percentage >= 80 and critical_vulns:
            high_scorers_with_vulns.append({
                'test_id': test_id,
                'score': f"{score}/{max_score} ({percentage:.0f}%)",
                'category': result.get('category', ''),
                'classification': classification,
                'critical_vulns': critical_vulns
            })

        # False Positive Type 3: PARTIAL/SECURE with multiple HIGH severity issues
        if classification in ['SECURE', 'PARTIAL'] and len(high_vulns) >= 2:
            false_positives.append({
                'test_id': test_id,
                'score': f"{score}/{max_score} ({percentage:.0f}%)",
                'category': result.get('category', ''),
                'classification': classification,
                'high_vulns': high_vulns
            })

    # Print results
    print(f"Total tests: {len(results)}")
    print(f"SECURE tests with CRITICAL vulnerabilities: {len(secure_with_critical)}")
    print(f"High scorers (>=80%) with CRITICAL vulnerabilities: {len(high_scorers_with_vulns)}")
    print(f"SECURE/PARTIAL with 2+ HIGH vulnerabilities: {len(false_positives)}\n")

    if secure_with_critical:
        print(f"\n{'='*80}")
        print("TYPE 1: SECURE Classification with CRITICAL Vulnerabilities")
        print("="*80)
        for fp in secure_with_critical[:10]:
            print(f"\n{fp['test_id']} ({fp['category']}) - Score: {fp['score']}")
            for vuln in fp['critical_vulns'][:2]:
                vuln_type = vuln.get('type', 'Unknown')
                desc = vuln.get('description', '')[:120]
                print(f"  [CRITICAL] {vuln_type}: {desc}")

    if high_scorers_with_vulns:
        print(f"\n{'='*80}")
        print("TYPE 2: High Scores (>=80%) with CRITICAL Vulnerabilities")
        print("="*80)
        for fp in high_scorers_with_vulns[:10]:
            print(f"\n{fp['test_id']} ({fp['category']}) - {fp['classification']} {fp['score']}")
            for vuln in fp['critical_vulns'][:2]:
                vuln_type = vuln.get('type', 'Unknown')
                desc = vuln.get('description', '')[:120]
                print(f"  [CRITICAL] {vuln_type}: {desc}")

    if false_positives:
        print(f"\n{'='*80}")
        print("TYPE 3: SECURE/PARTIAL with Multiple HIGH Severity Issues")
        print("="*80)
        for fp in false_positives[:10]:
            print(f"\n{fp['test_id']} ({fp['category']}) - {fp['classification']} {fp['score']}")
            print(f"  {len(fp['high_vulns'])} HIGH severity vulnerabilities:")
            for vuln in fp['high_vulns'][:3]:
                vuln_type = vuln.get('type', 'Unknown')
                desc = vuln.get('description', '')[:100]
                print(f"  [HIGH] {vuln_type}: {desc}")

    print(f"\n{'='*80}")
    print("SUMMARY")
    print("="*80)
    print(f"Total potential false positives: {len(secure_with_critical) + len(high_scorers_with_vulns) + len(false_positives)}")
    print(f"\nThese tests passed/scored highly but contain serious vulnerabilities.")
    print(f"With severity-weighted penalties, these would likely score lower/fail.")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        report_path = sys.argv[1]
    else:
        report_path = "reports/claude-opus-4-6_false_positive_analysis.json"

    if not Path(report_path).exists():
        print(f"Error: Report not found: {report_path}")
        print(f"Usage: python3 {sys.argv[0]} <report_path>")
        sys.exit(1)

    analyze_false_positives(report_path)
