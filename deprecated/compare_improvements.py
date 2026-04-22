#!/usr/bin/env python3
"""
Compare CodeLlama results before and after detector improvements.
Measures the reduction in false negatives (missed vulnerabilities).
"""

import json
import sys
from collections import defaultdict

def load_results(filepath):
    """Load JSON results file."""
    with open(filepath, 'r') as f:
        return json.load(f)

def analyze_results(results):
    """Analyze results and categorize by vulnerability type and status."""
    # Use categories directly from JSON
    return results.get('categories', {})

def calculate_detection_rate(stats):
    """Calculate vulnerability detection rate (not secure)."""
    rates = {}
    for vuln_type, counts in stats.items():
        total = counts['total']
        if total > 0:
            detected = counts['vulnerable'] + counts['partial']
            rate = (detected / total) * 100
            rates[vuln_type] = rate
    return rates

def compare_results(before_file, after_file):
    """Compare before and after results."""
    print("=" * 80)
    print("CODELLAMA DETECTOR IMPROVEMENTS COMPARISON")
    print("=" * 80)
    print()

    # Load results
    print(f"Loading baseline: {before_file}")
    before = load_results(before_file)
    print(f"Loading improved: {after_file}")
    after = load_results(after_file)
    print()

    # Analyze results
    before_stats = analyze_results(before)
    after_stats = analyze_results(after)

    # Calculate detection rates
    before_rates = calculate_detection_rate(before_stats)
    after_rates = calculate_detection_rate(after_stats)

    # Overall statistics
    print("=" * 80)
    print("OVERALL IMPROVEMENT")
    print("=" * 80)
    print()

    before_overall = before.get('summary', {})
    after_overall = after.get('summary', {})

    print(f"Baseline Score:  {before_overall.get('percentage', 0):.1f}%")
    print(f"Improved Score:  {after_overall.get('percentage', 0):.1f}%")
    improvement = after_overall.get('percentage', 0) - before_overall.get('percentage', 0)
    print(f"Overall Change:  {improvement:+.1f}%")
    print()

    print(f"Baseline:  {before_overall.get('total_score', 0)}/{before_overall.get('total_possible', 0)} points")
    print(f"Improved:  {after_overall.get('total_score', 0)}/{after_overall.get('total_possible', 0)} points")
    print()

    # Per-category improvements
    print("=" * 80)
    print("IMPROVEMENTS BY VULNERABILITY TYPE")
    print("=" * 80)
    print()

    # Get all vulnerability types
    all_types = sorted(set(before_stats.keys()) | set(after_stats.keys()))

    print(f"{'Type':<30} {'Before':<15} {'After':<15} {'Change':<15}")
    print("-" * 80)

    improvements = []
    for vuln_type in all_types:
        before_rate = before_rates.get(vuln_type, 0)
        after_rate = after_rates.get(vuln_type, 0)
        change = after_rate - before_rate

        before_str = f"{before_rate:.1f}%"
        after_str = f"{after_rate:.1f}%"
        change_str = f"{change:+.1f}%"

        print(f"{vuln_type:<30} {before_str:<15} {after_str:<15} {change_str:<15}")

        if change != 0:
            improvements.append((vuln_type, change))

    print()

    # Highlight significant improvements
    if improvements:
        print("=" * 80)
        print("SIGNIFICANT IMPROVEMENTS (sorted by magnitude)")
        print("=" * 80)
        print()

        improvements.sort(key=lambda x: abs(x[1]), reverse=True)

        for vuln_type, change in improvements[:10]:  # Top 10
            if change > 0:
                print(f"  ✓ {vuln_type:<30} {change:+.1f}% (improved detection)")
            elif change < 0:
                print(f"  ✗ {vuln_type:<30} {change:+.1f}% (reduced detection)")

    print()

    # Detailed breakdown
    print("=" * 80)
    print("DETAILED BREAKDOWN BY PRIORITY")
    print("=" * 80)
    print()

    # Priority 1: Command injection variable tracking, Secrets fallback
    print("Priority 1: Command Injection + Secrets Detection")
    print("-" * 40)
    for vuln_type in ['command_injection', 'hardcoded_secrets']:
        if vuln_type in before_rates:
            before_rate = before_rates[vuln_type]
            after_rate = after_rates.get(vuln_type, 0)
            change = after_rate - before_rate
            print(f"  {vuln_type:<25} {before_rate:.1f}% → {after_rate:.1f}% ({change:+.1f}%)")
    print()

    # Priority 2: PHP/TypeScript/Ruby support
    print("Priority 2: Multi-Language Support")
    print("-" * 40)
    print("  (Detectors now support PHP, TypeScript, Ruby)")
    print("  Impact measured in overall detection improvements above")
    print()

    # Priority 3: JWT algorithm confusion, Path traversal partial validation
    print("Priority 3: JWT + Path Traversal Enhancements")
    print("-" * 40)
    for vuln_type in ['insecure_jwt', 'path_traversal']:
        if vuln_type in before_rates:
            before_rate = before_rates[vuln_type]
            after_rate = after_rates.get(vuln_type, 0)
            change = after_rate - before_rate
            print(f"  {vuln_type:<25} {before_rate:.1f}% → {after_rate:.1f}% ({change:+.1f}%)")
    print()

    # Priority 4: React/Vue false positive reduction
    print("Priority 4: False Positive Reduction (XSS)")
    print("-" * 40)
    if 'xss' in before_rates:
        before_rate = before_rates['xss']
        after_rate = after_rates.get('xss', 0)
        change = after_rate - before_rate
        print(f"  xss                       {before_rate:.1f}% → {after_rate:.1f}% ({change:+.1f}%)")
        print("  (React/Vue safe patterns now correctly recognized)")
    print()

    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()

    positive_improvements = sum(1 for _, change in improvements if change > 0)
    negative_changes = sum(1 for _, change in improvements if change < 0)

    print(f"Vulnerability types improved:  {positive_improvements}")
    print(f"Vulnerability types regressed: {negative_changes}")
    print(f"Overall detection improvement: {improvement:+.1f}%")
    print()

    if improvement > 0:
        print("✓ Detector improvements successfully reduced false negatives")
    elif improvement == 0:
        print("→ No overall change in detection rate")
    else:
        print("✗ Overall detection rate decreased (investigate regressions)")

    print()
    print("=" * 80)

if __name__ == "__main__":
    before_file = "reports/codellama_before_fixes.json"
    after_file = "reports/codellama_after_all_improvements.json"

    compare_results(before_file, after_file)
