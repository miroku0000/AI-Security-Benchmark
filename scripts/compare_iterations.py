#!/usr/bin/env python3
"""
Compare two iterations to identify individual test changes.
"""

import json
import sys
from pathlib import Path


def load_results(file_path: str) -> dict:
    """Load validation results from JSON."""
    with open(file_path, 'r') as f:
        data = json.load(f)

    results = {}
    if 'detailed_results' in data:
        for item in data['detailed_results']:
            test_id = item.get('prompt_id')
            max_score = item.get('max_score', 0)

            # Only PRIMARY detector (max_score=2)
            if test_id and max_score == 2:
                results[test_id] = {
                    'score': item.get('score', 0),
                    'max_score': max_score,
                    'verdict': 'PASS' if item.get('score', 0) >= max_score else 'FAIL',
                    'category': item.get('category', 'unknown')
                }

    return results


def compare_iterations(old_results: dict, new_results: dict, model_name: str):
    """Compare two iterations for a single model."""
    changes = {
        'fixed': [],  # FAIL → PASS
        'broken': [],  # PASS → FAIL
        'unchanged': 0
    }

    all_tests = set(old_results.keys()) | set(new_results.keys())

    for test_id in all_tests:
        old = old_results.get(test_id)
        new = new_results.get(test_id)

        if not old or not new:
            continue

        if old['verdict'] != new['verdict']:
            if old['verdict'] == 'FAIL' and new['verdict'] == 'PASS':
                changes['fixed'].append({
                    'test_id': test_id,
                    'category': new['category'],
                    'old_score': f"{old['score']}/{old['max_score']}",
                    'new_score': f"{new['score']}/{new['max_score']}"
                })
            else:
                changes['broken'].append({
                    'test_id': test_id,
                    'category': new['category'],
                    'old_score': f"{old['score']}/{old['max_score']}",
                    'new_score': f"{new['score']}/{new['max_score']}"
                })
        else:
            changes['unchanged'] += 1

    return changes


def main():
    # Hardcoded paths for this analysis
    old_prefix = "iteration9_true_"
    new_prefix = "iteration10_"

    # Model names to compare
    models = [
        'claude-opus-4-6',
        'claude-sonnet-4-5',
        'gpt-4o',
        'gpt-5.4',
        'deepseek-coder',
        'cursor'
    ]

    print("=" * 100)
    print("ITERATION 10 vs ITERATION 9: CHANGE ANALYSIS - PRIMARY DETECTOR ONLY")
    print("=" * 100)

    all_changes = {
        'total_fixed': 0,
        'total_broken': 0,
        'model_changes': {}
    }

    for model in models:
        old_file = f"reports/{old_prefix}{model}.json"
        new_file = f"reports/{new_prefix}{model}.json"

        if not Path(old_file).exists() or not Path(new_file).exists():
            print(f"\n⚠️  Missing files for {model}")
            continue

        print(f"\nComparing {model}...")

        old_results = load_results(old_file)
        new_results = load_results(new_file)

        changes = compare_iterations(old_results, new_results, model)
        all_changes['model_changes'][model] = changes

        all_changes['total_fixed'] += len(changes['fixed'])
        all_changes['total_broken'] += len(changes['broken'])

        print(f"  Fixed: {len(changes['fixed'])}, Broken: {len(changes['broken'])}, Unchanged: {changes['unchanged']}")

    print("\n" + "=" * 100)
    print("SUMMARY")
    print("-" * 100)
    print(f"Total Fixed (FAIL → PASS):  {all_changes['total_fixed']}")
    print(f"Total Broken (PASS → FAIL): {all_changes['total_broken']}")
    print(f"Net Change:                 {all_changes['total_fixed'] - all_changes['total_broken']:+d}")

    # Show detailed changes
    if all_changes['total_fixed'] > 0:
        print("\n" + "=" * 100)
        print("FIXED TESTS (FAIL → PASS)")
        print("-" * 100)

        for model, changes in all_changes['model_changes'].items():
            if changes['fixed']:
                print(f"\n{model}:")
                for item in changes['fixed']:
                    print(f"  ✅ {item['test_id']:<35s} [{item['category']}] "
                          f"{item['old_score']} → {item['new_score']}")

    if all_changes['total_broken'] > 0:
        print("\n" + "=" * 100)
        print("BROKEN TESTS (PASS → FAIL)")
        print("-" * 100)

        for model, changes in all_changes['model_changes'].items():
            if changes['broken']:
                print(f"\n{model}:")
                for item in changes['broken']:
                    print(f"  ❌ {item['test_id']:<35s} [{item['category']}] "
                          f"{item['old_score']} → {item['new_score']}")

    print("\n" + "=" * 100)

    # Save detailed report
    output_file = "reports/iteration10_change_analysis.json"
    with open(output_file, 'w') as f:
        json.dump(all_changes, f, indent=2)

    print(f"\n✅ Detailed changes saved to: {output_file}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
