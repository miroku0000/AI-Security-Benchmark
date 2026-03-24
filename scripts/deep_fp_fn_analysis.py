#!/usr/bin/env python3
"""
Deep analysis of false positives and false negatives.
Examines specific code samples to validate detector accuracy.
"""
import json
from pathlib import Path
from collections import defaultdict

def analyze_sql_injection():
    """Analyze SQL injection tests - suspicious that 0% are vulnerable."""
    print("=" * 80)
    print("SQL INJECTION DEEP ANALYSIS")
    print("=" * 80)
    print()

    reports_dir = Path("reports")
    report_files = sorted(reports_dir.glob("*_20260321*.json"))

    sql_results = defaultdict(list)

    for report_file in report_files:
        try:
            with open(report_file) as f:
                data = json.load(f)

            model_name = data.get('model_name', 'Unknown')
            results = data.get('detailed_results', [])

            for result in results:
                if result.get('category') == 'sql_injection':
                    prompt_id = result.get('prompt_id', '')
                    score = result.get('score', 0)
                    max_score = result.get('max_score', 8)
                    vulns = result.get('vulnerabilities', [])

                    sql_results[prompt_id].append({
                        'model': model_name,
                        'score': score,
                        'max_score': max_score,
                        'status': 'SECURE' if score == max_score else ('PARTIAL' if score > 0 else 'VULNERABLE'),
                        'vulnerabilities': vulns
                    })
        except Exception as e:
            print(f"Error processing {report_file}: {e}")
            continue

    # Analyze patterns
    print(f"Found {len(sql_results)} SQL injection test prompts\n")

    for prompt_id, model_results in sorted(sql_results.items()):
        secure_count = sum(1 for r in model_results if r['status'] == 'SECURE')
        partial_count = sum(1 for r in model_results if r['status'] == 'PARTIAL')
        vuln_count = sum(1 for r in model_results if r['status'] == 'VULNERABLE')
        total = len(model_results)

        secure_pct = secure_count / total * 100 if total > 0 else 0

        print(f"\n{prompt_id}:")
        print(f"  Secure:     {secure_count:2d}/{total} ({secure_pct:5.1f}%)")
        print(f"  Partial:    {partial_count:2d}/{total}")
        print(f"  Vulnerable: {vuln_count:2d}/{total}")

        # If suspiciously high secure rate, flag it
        if secure_pct > 90:
            print(f"  ⚠️  SUSPICIOUS: {secure_pct:.1f}% secure - possible false negative")
            print(f"      Recommendation: Manually inspect code for actual SQL injection protection")
        elif secure_pct < 10:
            print(f"  ⚠️  SUSPICIOUS: {secure_pct:.1f}% secure - possible false positive")
            print(f"      Recommendation: Manually inspect detector logic")

    print()
    return sql_results


def analyze_business_logic():
    """Analyze business logic flaws - high vulnerability rate might be accurate."""
    print("=" * 80)
    print("BUSINESS LOGIC FLAW DEEP ANALYSIS")
    print("=" * 80)
    print()

    reports_dir = Path("reports")
    report_files = sorted(reports_dir.glob("*_20260321*.json"))

    business_results = defaultdict(list)

    for report_file in report_files:
        try:
            with open(report_file) as f:
                data = json.load(f)

            model_name = data.get('model_name', 'Unknown')
            results = data.get('detailed_results', [])

            for result in results:
                if result.get('category') == 'business_logic_flaw':
                    prompt_id = result.get('prompt_id', '')
                    score = result.get('score', 0)
                    max_score = result.get('max_score', 8)
                    vulns = result.get('vulnerabilities', [])

                    business_results[prompt_id].append({
                        'model': model_name,
                        'score': score,
                        'max_score': max_score,
                        'status': 'SECURE' if score == max_score else ('PARTIAL' if score > 0 else 'VULNERABLE'),
                        'vulnerabilities': vulns
                    })
        except Exception as e:
            print(f"Error processing {report_file}: {e}")
            continue

    print(f"Found {len(business_results)} business logic test prompts\n")

    # Find prompts with extreme results
    for prompt_id, model_results in sorted(business_results.items()):
        secure_count = sum(1 for r in model_results if r['status'] == 'SECURE')
        vuln_count = sum(1 for r in model_results if r['status'] == 'VULNERABLE')
        total = len(model_results)

        vuln_pct = vuln_count / total * 100 if total > 0 else 0

        # Only show prompts with extreme results
        if vuln_pct > 80 or vuln_pct < 20:
            print(f"\n{prompt_id}:")
            print(f"  Secure:     {secure_count:2d}/{total}")
            print(f"  Vulnerable: {vuln_count:2d}/{total} ({vuln_pct:5.1f}%)")

            if vuln_pct > 80:
                print(f"  → High vulnerability rate - likely accurate (business logic is hard)")
            elif vuln_pct < 20:
                print(f"  → Low vulnerability rate - models learned this pattern well")

    print()
    return business_results


def analyze_cross_model_patterns():
    """Look for patterns that are consistently wrong across all models."""
    print("=" * 80)
    print("CROSS-MODEL CONSISTENCY ANALYSIS")
    print("=" * 80)
    print()

    reports_dir = Path("reports")
    report_files = sorted(reports_dir.glob("*_20260321*.json"))

    # Track all results by prompt_id
    all_results = defaultdict(lambda: {'secure': 0, 'partial': 0, 'vulnerable': 0, 'total': 0})

    for report_file in report_files:
        try:
            with open(report_file) as f:
                data = json.load(f)

            results = data.get('detailed_results', [])

            for result in results:
                prompt_id = result.get('prompt_id', '')
                score = result.get('score', 0)
                max_score = result.get('max_score', 8)

                all_results[prompt_id]['total'] += 1
                if score == max_score:
                    all_results[prompt_id]['secure'] += 1
                elif score > 0:
                    all_results[prompt_id]['partial'] += 1
                else:
                    all_results[prompt_id]['vulnerable'] += 1
        except Exception as e:
            print(f"Error processing {report_file}: {e}")
            continue

    # Find prompts where ALL models get the same result
    print("Prompts where 100% of models have same result:\n")

    unanimous_secure = []
    unanimous_vuln = []

    for prompt_id, stats in sorted(all_results.items()):
        total = stats['total']
        if total == 0:
            continue

        secure_pct = stats['secure'] / total * 100
        vuln_pct = stats['vulnerable'] / total * 100

        if secure_pct == 100:
            unanimous_secure.append(prompt_id)
        elif vuln_pct == 100:
            unanimous_vuln.append(prompt_id)

    print(f"100% SECURE ({len(unanimous_secure)} prompts):")
    for prompt_id in unanimous_secure[:10]:  # Show first 10
        print(f"  - {prompt_id}")
    if len(unanimous_secure) > 10:
        print(f"  ... and {len(unanimous_secure) - 10} more")

    print()
    print(f"100% VULNERABLE ({len(unanimous_vuln)} prompts):")
    for prompt_id in unanimous_vuln[:10]:  # Show first 10
        print(f"  - {prompt_id}")
    if len(unanimous_vuln) > 10:
        print(f"  ... and {len(unanimous_vuln) - 10} more")

    print()
    print("⚠️  If a prompt is 100% secure or 100% vulnerable across ALL models,")
    print("    it might indicate:")
    print("    1. The prompt is too easy/hard (expected)")
    print("    2. Detector has systemic bias (possible FP/FN)")
    print("    3. All models learned this pattern (expected for common vulnerabilities)")
    print()


def analyze_specific_detectors():
    """Analyze specific detectors that might have issues."""
    print("=" * 80)
    print("DETECTOR-SPECIFIC ANALYSIS")
    print("=" * 80)
    print()

    reports_dir = Path("reports")
    report_files = sorted(reports_dir.glob("*_20260321*.json"))

    # Categories to focus on
    suspicious_categories = [
        'command_injection',
        'path_traversal',
        'xxe',
        'deserialization',
        'csrf',
    ]

    category_stats = defaultdict(lambda: {'secure': 0, 'partial': 0, 'vulnerable': 0, 'total': 0})

    for report_file in report_files:
        try:
            with open(report_file) as f:
                data = json.load(f)

            results = data.get('detailed_results', [])

            for result in results:
                category = result.get('category', '')
                if category in suspicious_categories:
                    score = result.get('score', 0)
                    max_score = result.get('max_score', 8)

                    category_stats[category]['total'] += 1
                    if score == max_score:
                        category_stats[category]['secure'] += 1
                    elif score > 0:
                        category_stats[category]['partial'] += 1
                    else:
                        category_stats[category]['vulnerable'] += 1
        except Exception as e:
            print(f"Error processing {report_file}: {e}")
            continue

    for category in sorted(suspicious_categories):
        stats = category_stats[category]
        if stats['total'] == 0:
            continue

        total = stats['total']
        secure_pct = stats['secure'] / total * 100
        vuln_pct = stats['vulnerable'] / total * 100

        print(f"{category:30s} {total:3d} tests")
        print(f"  Secure:     {stats['secure']:3d} ({secure_pct:5.1f}%)")
        print(f"  Partial:    {stats['partial']:3d}")
        print(f"  Vulnerable: {stats['vulnerable']:3d} ({vuln_pct:5.1f}%)")

        # Flag unusual patterns
        if secure_pct > 70:
            print(f"  ⚠️  High secure rate - verify detector isn't missing vulnerabilities")
        elif vuln_pct > 90:
            print(f"  ⚠️  Very high vuln rate - verify detector isn't too aggressive")

        print()


if __name__ == '__main__':
    print("\n" + "=" * 80)
    print("DEEP FALSE POSITIVE/NEGATIVE ANALYSIS")
    print("=" * 80)
    print()

    # Run all analyses
    sql_results = analyze_sql_injection()
    business_results = analyze_business_logic()
    analyze_cross_model_patterns()
    analyze_specific_detectors()

    print("=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)
    print()
    print("Recommendations:")
    print("1. Manually inspect code samples for categories flagged as suspicious")
    print("2. Compare detector logic with actual generated code")
    print("3. Focus on categories with >90% or <10% secure rates")
    print("4. Check prompts where 100% of models get same result")
    print()
