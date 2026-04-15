#!/usr/bin/env python3
"""
Compare validation results before and after detector fixes.

This script compares two validation JSON files to identify:
1. Tests that changed from VULNERABLE to SECURE (false positive fixes)
2. Tests that changed from SECURE to VULNERABLE (regressions - should be none)
3. Overall score improvements
4. Category-by-category comparison
"""

import json
import sys
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple


def load_results(file_path: str) -> Dict:
    """Load validation results from JSON file."""
    with open(file_path, 'r') as f:
        return json.load(f)


def categorize_result(score: int, max_score: int) -> str:
    """Categorize a test result as SECURE or VULNERABLE."""
    return "SECURE" if score >= max_score else "VULNERABLE"


def compare_results(before: Dict, after: Dict) -> Dict:
    """Compare before and after validation results."""

    comparison = {
        'total_tests': len(before),
        'false_positive_fixes': [],  # Changed from VULNERABLE to SECURE
        'regressions': [],  # Changed from SECURE to VULNERABLE
        'unchanged_vulnerable': [],
        'unchanged_secure': [],
        'score_improvements': [],  # Score increased but still vulnerable
        'score_decreases': [],  # Score decreased (should be investigated)
        'category_stats': defaultdict(lambda: {
            'total': 0,
            'improved': 0,
            'regressed': 0,
            'unchanged': 0
        })
    }

    for test_id in before.keys():
        if test_id not in after:
            print(f"Warning: {test_id} not found in after results")
            continue

        before_result = before[test_id]
        after_result = after[test_id]

        before_score = before_result.get('score', 0)
        after_score = after_result.get('score', 0)
        max_score = before_result.get('max_score', 2)
        category = before_result.get('category', 'unknown')

        before_status = categorize_result(before_score, max_score)
        after_status = categorize_result(after_score, max_score)

        # Update category stats
        comparison['category_stats'][category]['total'] += 1

        # Categorize the change
        if before_status == "VULNERABLE" and after_status == "SECURE":
            # False positive fix!
            comparison['false_positive_fixes'].append({
                'test_id': test_id,
                'category': category,
                'before_score': before_score,
                'after_score': after_score,
                'max_score': max_score
            })
            comparison['category_stats'][category]['improved'] += 1

        elif before_status == "SECURE" and after_status == "VULNERABLE":
            # Regression!
            comparison['regressions'].append({
                'test_id': test_id,
                'category': category,
                'before_score': before_score,
                'after_score': after_score,
                'max_score': max_score
            })
            comparison['category_stats'][category]['regressed'] += 1

        elif before_score < after_score:
            # Score improved but still vulnerable
            comparison['score_improvements'].append({
                'test_id': test_id,
                'category': category,
                'before_score': before_score,
                'after_score': after_score,
                'max_score': max_score
            })
            comparison['category_stats'][category]['improved'] += 1

        elif before_score > after_score:
            # Score decreased
            comparison['score_decreases'].append({
                'test_id': test_id,
                'category': category,
                'before_score': before_score,
                'after_score': after_score,
                'max_score': max_score
            })
            comparison['category_stats'][category]['regressed'] += 1

        else:
            # Unchanged
            if before_status == "VULNERABLE":
                comparison['unchanged_vulnerable'].append(test_id)
            else:
                comparison['unchanged_secure'].append(test_id)
            comparison['category_stats'][category]['unchanged'] += 1

    return comparison


def print_report(comparison: Dict, before_file: str, after_file: str):
    """Print a formatted comparison report."""

    print("=" * 90)
    print("VALIDATION RESULTS COMPARISON: BEFORE vs AFTER DETECTOR FIXES")
    print("=" * 90)
    print(f"\nBefore: {before_file}")
    print(f"After:  {after_file}")
    print(f"\nTotal Tests: {comparison['total_tests']}")

    # Summary statistics
    print("\n" + "=" * 90)
    print("SUMMARY")
    print("-" * 90)

    num_fixes = len(comparison['false_positive_fixes'])
    num_regressions = len(comparison['regressions'])
    num_improvements = len(comparison['score_improvements'])
    num_decreases = len(comparison['score_decreases'])

    print(f"✅ False Positive Fixes:     {num_fixes:4d} (VULNERABLE → SECURE)")
    print(f"⚠️  Regressions:              {num_regressions:4d} (SECURE → VULNERABLE)")
    print(f"📈 Score Improvements:       {num_improvements:4d} (Score increased, still vulnerable)")
    print(f"📉 Score Decreases:          {num_decreases:4d} (Score decreased)")
    print(f"➖ Unchanged:                {len(comparison['unchanged_vulnerable']) + len(comparison['unchanged_secure']):4d}")

    # False positive fixes (the main goal!)
    if comparison['false_positive_fixes']:
        print("\n" + "=" * 90)
        print("✅ FALSE POSITIVE FIXES (Tests Now Passing)")
        print("-" * 90)
        for fix in comparison['false_positive_fixes']:
            print(f"  {fix['test_id']:30s} [{fix['category']:20s}] {fix['before_score']}/{fix['max_score']} → {fix['after_score']}/{fix['max_score']}")

    # Regressions (should be none!)
    if comparison['regressions']:
        print("\n" + "=" * 90)
        print("⚠️  REGRESSIONS (Tests That Started Failing)")
        print("-" * 90)
        for reg in comparison['regressions']:
            print(f"  {reg['test_id']:30s} [{reg['category']:20s}] {reg['before_score']}/{reg['max_score']} → {reg['after_score']}/{reg['max_score']}")

    # Score improvements
    if comparison['score_improvements']:
        print("\n" + "=" * 90)
        print("📈 SCORE IMPROVEMENTS (Still Vulnerable, But Better)")
        print("-" * 90)
        for imp in sorted(comparison['score_improvements'],
                         key=lambda x: x['after_score'] - x['before_score'],
                         reverse=True)[:10]:  # Show top 10
            improvement = imp['after_score'] - imp['before_score']
            print(f"  {imp['test_id']:30s} [{imp['category']:20s}] {imp['before_score']}/{imp['max_score']} → {imp['after_score']}/{imp['max_score']} (+{improvement})")
        if len(comparison['score_improvements']) > 10:
            print(f"  ... and {len(comparison['score_improvements']) - 10} more")

    # Score decreases
    if comparison['score_decreases']:
        print("\n" + "=" * 90)
        print("📉 SCORE DECREASES (Need Investigation)")
        print("-" * 90)
        for dec in sorted(comparison['score_decreases'],
                         key=lambda x: x['before_score'] - x['after_score'],
                         reverse=True):
            decrease = dec['before_score'] - dec['after_score']
            print(f"  {dec['test_id']:30s} [{dec['category']:20s}] {dec['before_score']}/{dec['max_score']} → {dec['after_score']}/{dec['max_score']} (-{decrease})")

    # Category breakdown
    print("\n" + "=" * 90)
    print("CATEGORY BREAKDOWN")
    print("-" * 90)
    print(f"{'Category':<30s} {'Total':>6s} {'Improved':>8s} {'Regressed':>9s} {'Unchanged':>9s}")
    print("-" * 90)

    for category in sorted(comparison['category_stats'].keys()):
        stats = comparison['category_stats'][category]
        print(f"{category:<30s} {stats['total']:>6d} {stats['improved']:>8d} "
              f"{stats['regressed']:>9d} {stats['unchanged']:>9d}")

    print("=" * 90)

    # Expected fixes for Iteration 7
    print("\n" + "=" * 90)
    print("ITERATION 7 TARGET FIXES VERIFICATION")
    print("-" * 90)

    # Check for the specific fixes we made
    target_fixes = {
        'php_018': 'insecure_upload',
        'graphql_009': 'graphql_security'
    }

    for test_prefix, expected_category in target_fixes.items():
        found = False
        for fix in comparison['false_positive_fixes']:
            if test_prefix in fix['test_id']:
                print(f"✅ {test_prefix:15s} - FIXED as expected ({fix['category']})")
                found = True
                break
        if not found:
            # Check if it was already secure or still failing
            print(f"⚠️  {test_prefix:15s} - NOT in fixed list (check if already secure or still failing)")

    print("=" * 90)


def main():
    if len(sys.argv) != 3:
        print("Usage: python3 compare_validation_results.py <before.json> <after.json>")
        print("\nExample:")
        print("  python3 compare_validation_results.py \\")
        print("    reports/iteration5_validation_claude-opus-4-6.json \\")
        print("    reports/iteration7_claude-opus-4-6_fixed_detectors.json")
        sys.exit(1)

    before_file = sys.argv[1]
    after_file = sys.argv[2]

    # Validate files exist
    if not Path(before_file).exists():
        print(f"Error: Before file not found: {before_file}")
        sys.exit(1)

    if not Path(after_file).exists():
        print(f"Error: After file not found: {after_file}")
        sys.exit(1)

    # Load and compare results
    print("Loading validation results...")
    before = load_results(before_file)
    after = load_results(after_file)

    print("Comparing results...")
    comparison = compare_results(before, after)

    print_report(comparison, before_file, after_file)

    # Save detailed comparison to JSON
    output_file = "reports/iteration7_comparison_detailed.json"
    with open(output_file, 'w') as f:
        json.dump(comparison, f, indent=2)

    print(f"\n✅ Detailed comparison saved to: {output_file}")


if __name__ == "__main__":
    main()
