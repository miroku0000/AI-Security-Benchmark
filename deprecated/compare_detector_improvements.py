#!/usr/bin/env python3
"""
Compare CodeLlama analysis results before and after detector improvements.
Measures the impact of fixing false negatives in command injection and secrets detection.
"""
import json
import sys
from pathlib import Path

def load_report(filepath):
    """Load JSON report file."""
    with open(filepath, 'r') as f:
        return json.load(f)

def count_results(report):
    """Count secure/partial/vulnerable results from report."""
    results = report.get('detailed_results', [])

    secure = sum(1 for r in results if r.get('status') == 'SECURE')
    partial = sum(1 for r in results if r.get('status') == 'PARTIAL')
    vulnerable = sum(1 for r in results if r.get('status') == 'VULNERABLE')

    total_score = sum(r.get('score', 0) for r in results)
    max_score = sum(r.get('max_score', 0) for r in results)

    return {
        'secure': secure,
        'partial': partial,
        'vulnerable': vulnerable,
        'total': len(results),
        'score': total_score,
        'max_score': max_score,
        'percentage': (total_score / max_score * 100) if max_score > 0 else 0
    }

def find_changed_files(before_report, after_report):
    """Find files that changed status between reports."""
    before_results = {r['prompt_id']: r for r in before_report.get('detailed_results', [])}
    after_results = {r['prompt_id']: r for r in after_report.get('detailed_results', [])}

    changed = []

    for prompt_id, after in after_results.items():
        if prompt_id in before_results:
            before = before_results[prompt_id]
            if before.get('status') != after.get('status') or before.get('score') != after.get('score'):
                changed.append({
                    'file': prompt_id,
                    'code_path': after.get('generated_code_path', 'N/A'),
                    'before_status': before.get('status'),
                    'before_score': f"{before.get('score')}/{before.get('max_score')}",
                    'after_status': after.get('status'),
                    'after_score': f"{after.get('score')}/{after.get('max_score')}",
                    'change': after.get('score', 0) - before.get('score', 0)
                })

    return sorted(changed, key=lambda x: x['change'])

def main():
    before_path = Path('reports/codellama_before_fixes.json')
    after_path = Path('reports/codellama_after_fixes.json')

    if not before_path.exists():
        print(f"ERROR: Before report not found: {before_path}")
        sys.exit(1)

    if not after_path.exists():
        print(f"ERROR: After report not found: {after_path}")
        sys.exit(1)

    print("CodeLlama Detector Improvements Analysis")
    print("=" * 80)
    print()

    # Load reports
    before_report = load_report(before_path)
    after_report = load_report(after_path)

    # Count results
    before_counts = count_results(before_report)
    after_counts = count_results(after_report)

    # Print summary
    print("OVERALL RESULTS")
    print("-" * 80)
    print(f"{'Metric':<30} {'Before':<20} {'After':<20} {'Change':<10}")
    print("-" * 80)

    print(f"{'Total Files Analyzed':<30} {before_counts['total']:<20} {after_counts['total']:<20} {after_counts['total'] - before_counts['total']:+d}")
    print(f"{'Secure':<30} {before_counts['secure']:<20} {after_counts['secure']:<20} {after_counts['secure'] - before_counts['secure']:+d}")
    print(f"{'Partial':<30} {before_counts['partial']:<20} {after_counts['partial']:<20} {after_counts['partial'] - before_counts['partial']:+d}")
    print(f"{'Vulnerable':<30} {before_counts['vulnerable']:<20} {after_counts['vulnerable']:<20} {after_counts['vulnerable'] - before_counts['vulnerable']:+d}")
    print()
    print(f"{'Score':<30} {before_counts['score']}/{before_counts['max_score']:<19} {after_counts['score']}/{after_counts['max_score']:<19} {after_counts['score'] - before_counts['score']:+d}")
    print(f"{'Percentage':<30} {before_counts['percentage']:.1f}%{'':<16} {after_counts['percentage']:.1f}%{'':<16} {after_counts['percentage'] - before_counts['percentage']:+.1f}pp")
    print()

    # Find changed files
    changed_files = find_changed_files(before_report, after_report)

    if changed_files:
        print()
        print("FILES WITH CHANGED STATUS/SCORE")
        print("-" * 80)
        print(f"{'File':<40} {'Before':<15} {'After':<15} {'Change':<10}")
        print("-" * 80)

        for change in changed_files:
            print(f"{change['file']:<40} {change['before_status']:<6} {change['before_score']:<8} {change['after_status']:<6} {change['after_score']:<8} {change['change']:+d}")

        print()
        print(f"Total files with changes: {len(changed_files)}")

        # Specific false negative corrections
        print()
        print("CONFIRMED FALSE NEGATIVE CORRECTIONS")
        print("-" * 80)

        cmd_003 = next((c for c in changed_files if 'cmd_003' in c['file']), None)
        if cmd_003:
            print(f"✓ cmd_003.py: {cmd_003['before_status']} ({cmd_003['before_score']}) → {cmd_003['after_status']} ({cmd_003['after_score']})")
            print("  Issue: Command injection with variable data flow not tracked")
            print("  Fix: Added Pattern 1b to track f-strings/concatenation in variables")

        secrets_002 = next((c for c in changed_files if 'secrets_002' in c['file']), None)
        if secrets_002:
            print(f"✓ secrets_002.js: {secrets_002['before_status']} ({secrets_002['before_score']}) → {secrets_002['after_status']} ({secrets_002['after_score']})")
            print("  Issue: Environment variable fallback with hardcoded secret not detected")
            print("  Fix: Added Pattern 1 to detect process.env.X || 'secret' patterns")
    else:
        print()
        print("No files changed status/score between reports.")

    print()
    print("=" * 80)
    print("Analysis complete!")
    print()

    # Return non-zero if score decreased
    if after_counts['score'] < before_counts['score']:
        print("WARNING: Score decreased after fixes!")
        sys.exit(1)
    elif after_counts['score'] == before_counts['score']:
        print("INFO: Score unchanged (fixes may not have affected analyzed files)")
    else:
        print(f"SUCCESS: Score improved by {after_counts['score'] - before_counts['score']} points ({after_counts['percentage'] - before_counts['percentage']:+.1f}pp)")

if __name__ == '__main__':
    main()
