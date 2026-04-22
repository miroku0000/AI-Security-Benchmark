#!/usr/bin/env python3
"""
Extract category-level statistics from benchmark validation results
"""
import json
import sys
from collections import defaultdict

def analyze_categories(json_file):
    with open(json_file, 'r') as f:
        data = json.load(f)

    # Group by category
    category_stats = defaultdict(lambda: {'total': 0, 'vulnerable': 0, 'secure': 0, 'scores': []})

    for test_id, result in data.items():
        category = result.get('category', 'unknown')
        score = result.get('score', 0)
        max_score = result.get('max_score', 2)

        category_stats[category]['total'] += 1
        category_stats[category]['scores'].append(score)

        if score < max_score:
            category_stats[category]['vulnerable'] += 1
        else:
            category_stats[category]['secure'] += 1

    # Calculate percentages and sort by vulnerability rate
    results = []
    for category, stats in category_stats.items():
        vuln_rate = (stats['vulnerable'] / stats['total'] * 100) if stats['total'] > 0 else 0
        secure_rate = (stats['secure'] / stats['total'] * 100) if stats['total'] > 0 else 0
        avg_score = sum(stats['scores']) / len(stats['scores']) if stats['scores'] else 0

        results.append({
            'category': category,
            'total': stats['total'],
            'vulnerable': stats['vulnerable'],
            'secure': stats['secure'],
            'vuln_rate': vuln_rate,
            'secure_rate': secure_rate,
            'avg_score': avg_score
        })

    # Sort by vulnerability rate (descending) then by total tests (descending)
    results.sort(key=lambda x: (x['vuln_rate'], x['total']), reverse=True)

    return results

def print_results(results, top_n=20):
    print("=" * 100)
    print(f"{'Category':<35} {'Total':<8} {'Vuln':<8} {'Secure':<8} {'Vuln%':<10} {'Secure%':<10} {'AvgScore':<10}")
    print("=" * 100)

    for i, r in enumerate(results[:top_n], 1):
        print(f"{i:2}. {r['category']:<32} {r['total']:<8} {r['vulnerable']:<8} {r['secure']:<8} "
              f"{r['vuln_rate']:>6.1f}%    {r['secure_rate']:>6.1f}%    {r['avg_score']:>6.2f}/2")

    print("=" * 100)
    print(f"\nShowing top {min(top_n, len(results))} of {len(results)} categories")

    # Calculate totals
    total_tests = sum(r['total'] for r in results)
    total_vuln = sum(r['vulnerable'] for r in results)
    total_secure = sum(r['secure'] for r in results)

    print(f"\nOverall: {total_tests} tests, {total_vuln} vulnerable ({total_vuln/total_tests*100:.1f}%), "
          f"{total_secure} secure ({total_secure/total_tests*100:.1f}%)")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 extract_category_stats.py <validation_json_file> [top_n]")
        sys.exit(1)

    json_file = sys.argv[1]
    top_n = int(sys.argv[2]) if len(sys.argv) > 2 else 20

    results = analyze_categories(json_file)
    print_results(results, top_n)
