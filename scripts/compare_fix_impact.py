#!/usr/bin/env python3
"""
Compare benchmark results before and after detector fixes.
Analyzes impact of buffer overflow and SQL injection detector improvements.
"""
import json
from pathlib import Path
from collections import defaultdict

def load_report(file_path):
    """Load a JSON report file."""
    try:
        with open(file_path) as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {file_path}: {e}")
        return None

def compare_reports():
    """Compare before/after reports for all models."""

    reports_dir = Path("reports")
    backup_dir = reports_dir / "pre-fix-backup"

    if not backup_dir.exists():
        print("ERROR: No backup directory found at reports/pre-fix-backup/")
        print("Please run retest_with_fixes.sh first to create backups and new reports.")
        return

    print("=" * 80)
    print("DETECTOR FIX IMPACT ANALYSIS")
    print("=" * 80)
    print()
    print("Comparing:")
    print("  BEFORE: reports/pre-fix-backup/*_208point_20260321.json")
    print("  AFTER:  reports/*_208point_20260321_fixed.json")
    print()
    print("=" * 80)
    print()

    # Track changes
    total_models = 0
    improved_models = 0
    unchanged_models = 0
    regressed_models = 0

    model_changes = []

    # Find all models with both before/after reports
    before_files = list(backup_dir.glob("*_208point_20260321.json"))

    for before_file in sorted(before_files):
        model_name = before_file.stem.replace("_208point_20260321", "")
        after_file = reports_dir / f"{model_name}_208point_20260321_fixed.json"

        if not after_file.exists():
            print(f"⊘ {model_name}: No 'after' report found, skipping")
            continue

        # Load reports
        before = load_report(before_file)
        after = load_report(after_file)

        if not before or not after:
            continue

        total_models += 1

        # Extract scores
        before_score = before.get('overall_score', 0)
        before_max = before.get('overall_max_score', 1)
        before_pct = (before_score / before_max * 100) if before_max > 0 else 0

        after_score = after.get('overall_score', 0)
        after_max = after.get('overall_max_score', 1)
        after_pct = (after_score / after_max * 100) if after_max > 0 else 0

        score_diff = after_score - before_score
        pct_diff = after_pct - before_pct

        # Categorize change
        if score_diff > 0:
            status = "✓ IMPROVED"
            improved_models += 1
        elif score_diff < 0:
            status = "✗ REGRESSED"
            regressed_models += 1
        else:
            status = "→ UNCHANGED"
            unchanged_models += 1

        model_changes.append({
            'model': model_name,
            'before_score': before_score,
            'before_max': before_max,
            'before_pct': before_pct,
            'after_score': after_score,
            'after_max': after_max,
            'after_pct': after_pct,
            'score_diff': score_diff,
            'pct_diff': pct_diff,
            'status': status
        })

    # Print detailed results
    print(f"Analyzed {total_models} models\n")

    # Sort by score difference (most improved first)
    model_changes.sort(key=lambda x: x['score_diff'], reverse=True)

    print("MODEL COMPARISON:")
    print()
    print(f"{'Model':<35} {'Before':>12} {'After':>12} {'Change':>12} {'Status':>12}")
    print("-" * 85)

    for change in model_changes:
        model = change['model'][:33]
        before = f"{change['before_score']}/{change['before_max']} ({change['before_pct']:.1f}%)"
        after = f"{change['after_score']}/{change['after_max']} ({change['after_pct']:.1f}%)"
        diff = f"{change['score_diff']:+d} ({change['pct_diff']:+.1f}%)"
        status = change['status']

        print(f"{model:<35} {before:>12} {after:>12} {diff:>12} {status:>12}")

    print()
    print("=" * 80)
    print()
    print("SUMMARY:")
    print(f"  Total Models:     {total_models}")
    print(f"  Improved:         {improved_models} ({improved_models/total_models*100:.1f}%)")
    print(f"  Unchanged:        {unchanged_models} ({unchanged_models/total_models*100:.1f}%)")
    print(f"  Regressed:        {regressed_models} ({regressed_models/total_models*100:.1f}%)")
    print()

    # Calculate aggregate impact
    total_before = sum(c['before_score'] for c in model_changes)
    total_after = sum(c['after_score'] for c in model_changes)
    total_max = sum(c['after_max'] for c in model_changes)

    avg_before = total_before / total_models if total_models > 0 else 0
    avg_after = total_after / total_models if total_models > 0 else 0
    avg_diff = avg_after - avg_before

    before_pct = (total_before / total_max * 100) if total_max > 0 else 0
    after_pct = (total_after / total_max * 100) if total_max > 0 else 0
    pct_diff = after_pct - before_pct

    print(f"AGGREGATE IMPACT:")
    print(f"  Total Score Before:  {total_before}/{total_max} ({before_pct:.1f}%)")
    print(f"  Total Score After:   {total_after}/{total_max} ({after_pct:.1f}%)")
    print(f"  Net Change:          {total_after - total_before:+d} points ({pct_diff:+.1f}%)")
    print(f"  Avg Per Model:       {avg_diff:+.1f} points")
    print()

    # Analyze category-specific changes
    print("=" * 80)
    print()
    print("CATEGORY-SPECIFIC IMPACT:")
    print()

    category_changes = defaultdict(lambda: {'before': 0, 'after': 0, 'count': 0})

    for before_file in before_files:
        model_name = before_file.stem.replace("_208point_20260321", "")
        after_file = reports_dir / f"{model_name}_208point_20260321_fixed.json"

        if not after_file.exists():
            continue

        before = load_report(before_file)
        after = load_report(after_file)

        if not before or not after:
            continue

        # Compare detailed results by category
        before_results = {r['prompt_id']: r for r in before.get('detailed_results', [])}
        after_results = {r['prompt_id']: r for r in after.get('detailed_results', [])}

        for prompt_id in before_results:
            if prompt_id not in after_results:
                continue

            category = before_results[prompt_id].get('category', 'unknown')
            before_score = before_results[prompt_id].get('score', 0)
            after_score = after_results[prompt_id].get('score', 0)

            category_changes[category]['before'] += before_score
            category_changes[category]['after'] += after_score
            category_changes[category]['count'] += 1

    # Print category changes sorted by impact
    category_diffs = []
    for cat, stats in category_changes.items():
        diff = stats['after'] - stats['before']
        if stats['count'] > 0:
            avg_diff = diff / stats['count']
            category_diffs.append((cat, diff, avg_diff, stats['count']))

    category_diffs.sort(key=lambda x: x[1], reverse=True)

    print(f"{'Category':<30} {'Total Change':>15} {'Avg Per Test':>15} {'# Tests':>10}")
    print("-" * 70)

    for cat, total_diff, avg_diff, count in category_diffs:
        if total_diff != 0:  # Only show categories with changes
            print(f"{cat:<30} {total_diff:+15d} {avg_diff:+15.2f} {count:>10d}")

    print()
    print("=" * 80)
    print()

    # Highlight key findings
    print("KEY FINDINGS:")
    print()

    sql_change = category_changes.get('sql_injection', {'before': 0, 'after': 0, 'count': 0})
    if sql_change['count'] > 0:
        sql_diff = sql_change['after'] - sql_change['before']
        sql_avg = sql_diff / sql_change['count']
        print(f"1. SQL Injection Fix Impact:")
        print(f"   - Total change: {sql_diff:+d} points across {sql_change['count']} tests")
        print(f"   - Average per test: {sql_avg:+.2f} points")
        print(f"   - Status: {'✓ Fixed false positives' if sql_diff > 0 else '→ No change detected'}")
        print()

    buffer_change = category_changes.get('buffer_overflow', {'before': 0, 'after': 0, 'count': 0})
    if buffer_change['count'] > 0:
        buffer_diff = buffer_change['after'] - buffer_change['before']
        buffer_avg = buffer_diff / buffer_change['count']
        print(f"2. Buffer Overflow Fix Impact:")
        print(f"   - Total change: {buffer_diff:+d} points across {buffer_change['count']} tests")
        print(f"   - Average per test: {buffer_avg:+.2f} points")
        print(f"   - Status: {'✓ Previously fixed' if buffer_diff == 0 else 'Check for issues'}")
        print()

    print("=" * 80)

if __name__ == '__main__':
    compare_reports()
