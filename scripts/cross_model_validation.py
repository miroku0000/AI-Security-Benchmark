#!/usr/bin/env python3
"""
Cross-model validation to identify detector inconsistencies.

This script compares validation results across multiple models to find:
1. Tests where different models produce different verdicts (SECURE vs VULNERABLE)
2. High variance in scores for the same test across models
3. Potential false positives/negatives indicated by inconsistent detector behavior

The hypothesis: If the SAME test case produces DIFFERENT verdicts for different models,
it may indicate the detector is sensitive to code style rather than actual vulnerabilities.
"""

import json
import sys
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple


def load_results(file_path: str) -> Dict:
    """Load validation results from JSON file."""
    with open(file_path, 'r') as f:
        data = json.load(f)

    # Handle both flat and list-based structures
    if 'detailed_results' in data:
        # List-based structure from runner.py
        results = {}
        for item in data['detailed_results']:
            test_id = item.get('prompt_id')
            if test_id:
                results[test_id] = {
                    'score': item.get('score', 0),
                    'max_score': item.get('max_score', 2),
                    'category': item.get('category', 'unknown'),
                    'primary_detector_result': item.get('primary_detector_result', 'UNKNOWN')
                }
        return results
    elif 'categories' in data:
        # Old nested structure
        results = {}
        for category_name, category_data in data.get('categories', {}).items():
            for test_id, test_result in category_data.get('tests', {}).items():
                results[test_id] = test_result
        return results
    else:
        # Flat structure
        return data


def categorize_result(score: int, max_score: int) -> str:
    """Categorize a test result as SECURE or VULNERABLE."""
    return "SECURE" if score >= max_score else "VULNERABLE"


def compare_across_models(model_results: Dict[str, Dict]) -> Dict:
    """Compare test results across multiple models."""

    # Get all unique test IDs
    all_test_ids = set()
    for results in model_results.values():
        all_test_ids.update(results.keys())

    comparison = {
        'total_tests': len(all_test_ids),
        'inconsistent_verdicts': [],  # Different SECURE/VULNERABLE verdicts
        'high_variance': [],  # Large score differences
        'always_secure': [],
        'always_vulnerable': [],
        'category_inconsistency': defaultdict(int)
    }

    for test_id in sorted(all_test_ids):
        # Collect results from all models
        model_data = {}
        for model_name, results in model_results.items():
            if test_id in results:
                result = results[test_id]
                score = result.get('score', 0)
                max_score = result.get('max_score', 2)
                status = categorize_result(score, max_score)
                category = result.get('category', 'unknown')

                model_data[model_name] = {
                    'score': score,
                    'max_score': max_score,
                    'status': status,
                    'category': category
                }

        if len(model_data) < 2:
            continue  # Need at least 2 models to compare

        # Check for inconsistent verdicts
        statuses = [data['status'] for data in model_data.values()]
        unique_statuses = set(statuses)

        if len(unique_statuses) > 1:
            # Mixed SECURE/VULNERABLE verdicts - potential detector issue!
            secure_count = statuses.count('SECURE')
            vulnerable_count = statuses.count('VULNERABLE')

            # Get category
            category = list(model_data.values())[0]['category']

            comparison['inconsistent_verdicts'].append({
                'test_id': test_id,
                'category': category,
                'secure_count': secure_count,
                'vulnerable_count': vulnerable_count,
                'total_models': len(model_data),
                'models': {
                    model: {
                        'status': data['status'],
                        'score': f"{data['score']}/{data['max_score']}"
                    }
                    for model, data in model_data.items()
                }
            })

            comparison['category_inconsistency'][category] += 1

        elif 'SECURE' in unique_statuses:
            comparison['always_secure'].append(test_id)
        else:
            comparison['always_vulnerable'].append(test_id)

        # Check for high variance in scores (even if verdict is same)
        scores = [data['score'] for data in model_data.values()]
        if len(scores) >= 3:
            score_range = max(scores) - min(scores)
            if score_range >= 2:  # Significant variance
                comparison['high_variance'].append({
                    'test_id': test_id,
                    'category': list(model_data.values())[0]['category'],
                    'scores': scores,
                    'range': score_range,
                    'models': {
                        model: f"{data['score']}/{data['max_score']}"
                        for model, data in model_data.items()
                    }
                })

    return comparison


def print_report(comparison: Dict, models: List[str]):
    """Print formatted cross-model comparison report."""

    print("=" * 100)
    print("ITERATION 8: CROSS-MODEL DETECTOR VALIDATION")
    print("=" * 100)
    print(f"\nModels Compared: {', '.join(models)}")
    print(f"Total Tests Analyzed: {comparison['total_tests']}")

    # Summary statistics
    print("\n" + "=" * 100)
    print("SUMMARY")
    print("-" * 100)

    num_inconsistent = len(comparison['inconsistent_verdicts'])
    num_variance = len(comparison['high_variance'])
    num_always_secure = len(comparison['always_secure'])
    num_always_vulnerable = len(comparison['always_vulnerable'])

    print(f"⚠️  Inconsistent Verdicts:     {num_inconsistent:4d} (Different SECURE/VULNERABLE across models)")
    print(f"📊 High Score Variance:       {num_variance:4d} (Score range ≥ 2 points)")
    print(f"✅ Always Secure:             {num_always_secure:4d} (All models agree: SECURE)")
    print(f"❌ Always Vulnerable:         {num_always_vulnerable:4d} (All models agree: VULNERABLE)")

    # Inconsistent verdicts (PRIMARY FOCUS - potential detector issues!)
    if comparison['inconsistent_verdicts']:
        print("\n" + "=" * 100)
        print("⚠️  INCONSISTENT VERDICTS (Potential Detector Issues)")
        print("-" * 100)
        print(f"{'Test ID':<35s} {'Category':<25s} {'Secure':>6s} {'Vuln':>5s} {'Total':>5s}")
        print("-" * 100)

        # Sort by most controversial (closest to 50/50 split)
        sorted_inconsistent = sorted(
            comparison['inconsistent_verdicts'],
            key=lambda x: abs(x['secure_count'] - x['vulnerable_count'])
        )

        for item in sorted_inconsistent[:30]:  # Show top 30
            print(f"{item['test_id']:<35s} {item['category']:<25s} "
                  f"{item['secure_count']:>6d} {item['vulnerable_count']:>5d} {item['total_models']:>5d}")

        if len(sorted_inconsistent) > 30:
            print(f"\n  ... and {len(sorted_inconsistent) - 30} more inconsistent tests")

        # Show detailed breakdown for most controversial cases
        print("\n" + "=" * 100)
        print("DETAILED BREAKDOWN - Most Controversial Cases (50/50 splits)")
        print("-" * 100)

        controversial = [
            item for item in sorted_inconsistent
            if abs(item['secure_count'] - item['vulnerable_count']) <= 1
        ][:10]  # Top 10 most split

        for item in controversial:
            print(f"\n{item['test_id']} [{item['category']}]")
            print(f"  Split: {item['secure_count']} SECURE / {item['vulnerable_count']} VULNERABLE")
            for model, data in sorted(item['models'].items()):
                status_emoji = "✅" if data['status'] == 'SECURE' else "❌"
                print(f"    {status_emoji} {model:<30s}: {data['status']:<12s} (score: {data['score']})")

    # High variance scores
    if comparison['high_variance']:
        print("\n" + "=" * 100)
        print("📊 HIGH SCORE VARIANCE (Same verdict, different scores)")
        print("-" * 100)

        sorted_variance = sorted(
            comparison['high_variance'],
            key=lambda x: x['range'],
            reverse=True
        )[:15]  # Top 15

        for item in sorted_variance:
            print(f"\n{item['test_id']} [{item['category']}] - Range: {item['range']}")
            for model, score in sorted(item['models'].items()):
                print(f"    {model:<30s}: {score}")

    # Category breakdown
    if comparison['category_inconsistency']:
        print("\n" + "=" * 100)
        print("CATEGORY BREAKDOWN - Inconsistency by Category")
        print("-" * 100)
        print(f"{'Category':<35s} {'Inconsistent Tests':>20s}")
        print("-" * 100)

        for category in sorted(comparison['category_inconsistency'].keys(),
                             key=lambda k: comparison['category_inconsistency'][k],
                             reverse=True):
            count = comparison['category_inconsistency'][category]
            print(f"{category:<35s} {count:>20d}")

    print("\n" + "=" * 100)
    print("INTERPRETATION")
    print("-" * 100)
    print("""
Inconsistent verdicts suggest potential detector issues:
1. Detector may be sensitive to code style/syntax rather than actual vulnerabilities
2. Some models may trigger different detection patterns
3. Could indicate false positives or false negatives

Next Steps:
1. Manually review controversial cases (50/50 splits)
2. Identify root causes (code style, language differences, detector logic)
3. Fix detector to be consistent across code styles
4. Re-validate all models with fixed detector
    """)
    print("=" * 100)


def main():
    if len(sys.argv) < 3:
        print("Usage: python3 cross_model_validation.py <model1_analysis.json> <model2_analysis.json> [model3_analysis.json ...]")
        print("\nExample:")
        print("  python3 cross_model_validation.py \\")
        print("    reports/claude-opus-4-6_temp0.0_analysis.json \\")
        print("    reports/claude-sonnet-4-5_analysis.json \\")
        print("    reports/gpt-4o_analysis.json")
        sys.exit(1)

    # Load results from all models
    model_results = {}
    models = []

    for file_path in sys.argv[1:]:
        if not Path(file_path).exists():
            print(f"Warning: File not found: {file_path}")
            continue

        # Extract model name from filename
        model_name = Path(file_path).stem.replace('_analysis', '').replace('_temp0.0', '')
        models.append(model_name)

        print(f"Loading: {model_name} from {file_path}")
        model_results[model_name] = load_results(file_path)

    if len(model_results) < 2:
        print("Error: Need at least 2 models to compare")
        sys.exit(1)

    print(f"\nComparing {len(model_results)} models...")
    comparison = compare_across_models(model_results)

    print_report(comparison, models)

    # Save detailed comparison to JSON
    output_file = "reports/iteration8_cross_model_comparison.json"
    with open(output_file, 'w') as f:
        json.dump(comparison, f, indent=2)

    print(f"\n✅ Detailed comparison saved to: {output_file}")

    # Return exit code based on findings
    num_inconsistent = len(comparison['inconsistent_verdicts'])
    if num_inconsistent > 0:
        print(f"\n⚠️  Found {num_inconsistent} tests with inconsistent verdicts - manual review recommended")
        return 1
    else:
        print("\n✅ All tests have consistent verdicts across models")
        return 0


if __name__ == "__main__":
    sys.exit(main())
