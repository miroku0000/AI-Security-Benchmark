#!/usr/bin/env python3
"""
Analyze what vulnerabilities Codex.app with Security Skill missed.
"""

import json
import glob
import yaml
from collections import defaultdict

def load_prompts():
    """Load prompts with metadata."""
    with open('prompts/prompts.yaml') as f:
        data = yaml.safe_load(f)
    return {p['id']: p for p in data['prompts']}

def analyze_codex_failures():
    """Analyze failures from Codex.app security skill."""

    # Find the Codex.app security skill report
    reports = glob.glob("reports/codex-app-security-skill*_20260323.json")

    if not reports:
        print("No Codex.app security skill report found!")
        return

    report_path = reports[0]

    with open(report_path) as f:
        data = json.load(f)

    prompts = load_prompts()

    # Get only Python/JavaScript prompts
    original_ids = {pid for pid, p in prompts.items() if p.get('language') in ['python', 'javascript']}

    # Analyze results
    all_results = data.get('detailed_results', [])

    failures = []
    partial_failures = []
    successes = []

    for result in all_results:
        prompt_id = result.get('prompt_id')

        # Skip if not in original 66
        if prompt_id not in original_ids:
            continue

        score = result.get('score', 0)
        max_score = result.get('max_score', 2)

        prompt_info = prompts.get(prompt_id, {})

        result_data = {
            'prompt_id': prompt_id,
            'score': score,
            'max_score': max_score,
            'vuln_type': prompt_info.get('vulnerability_type', 'unknown'),
            'language': prompt_info.get('language', 'unknown'),
            'description': prompt_info.get('description', 'No description'),
            'details': result.get('details', 'No details')
        }

        if score == 0:
            failures.append(result_data)
        elif score < max_score:
            partial_failures.append(result_data)
        else:
            successes.append(result_data)

    # Group failures by vulnerability type
    failures_by_type = defaultdict(list)
    for failure in failures:
        failures_by_type[failure['vuln_type']].append(failure)

    partial_by_type = defaultdict(list)
    for partial in partial_failures:
        partial_by_type[partial['vuln_type']].append(partial)

    # Print results
    print("=" * 140)
    print("CODEX.APP (SECURITY SKILL) FAILURE ANALYSIS - 66 PROMPTS (Python + JavaScript)")
    print("=" * 140)
    print()

    total_prompts = len(failures) + len(partial_failures) + len(successes)
    total_score = sum(r['score'] for r in all_results if r.get('prompt_id') in original_ids)
    total_max = sum(r['max_score'] for r in all_results if r.get('prompt_id') in original_ids)
    percentage = (total_score / total_max * 100) if total_max > 0 else 0

    print(f"Overall Performance: {total_score}/{total_max} ({percentage:.1f}%)")
    print(f"Total Prompts (Py/JS): {total_prompts}")
    print(f"Complete Failures (0 points): {len(failures)}")
    print(f"Partial Failures (1 point): {len(partial_failures)}")
    print(f"Complete Successes (2 points): {len(successes)}")
    print()
    print("=" * 140)
    print()

    # Complete failures
    if failures:
        print("COMPLETE FAILURES (0/2 points):")
        print()

        for vuln_type in sorted(failures_by_type.keys()):
            fails = failures_by_type[vuln_type]
            print(f"\n{vuln_type.upper().replace('_', ' ')} ({len(fails)} failures):")
            print("-" * 100)

            for fail in fails:
                print(f"\n  Prompt: {fail['prompt_id']}")
                print(f"  Language: {fail['language']}")
                print(f"  Description: {fail['description']}")
                print(f"  Details: {fail['details']}")

        print()
        print("=" * 140)

    # Partial failures
    if partial_failures:
        print()
        print("PARTIAL FAILURES (1/2 points):")
        print()

        for vuln_type in sorted(partial_by_type.keys()):
            partials = partial_by_type[vuln_type]
            print(f"\n{vuln_type.upper().replace('_', ' ')} ({len(partials)} partial failures):")
            print("-" * 100)

            for partial in partials:
                print(f"\n  Prompt: {partial['prompt_id']}")
                print(f"  Language: {partial['language']}")
                print(f"  Description: {partial['description']}")
                print(f"  Details: {partial['details']}")

        print()
        print("=" * 140)

    # Summary by vulnerability type
    print()
    print("SUMMARY BY VULNERABILITY TYPE:")
    print()
    print(f"{'Vulnerability Type':<35} {'Total':<8} {'Failed':<8} {'Partial':<8} {'Success':<8} {'Success Rate'}")
    print("-" * 100)

    all_vuln_types = set()
    all_vuln_types.update(failures_by_type.keys())
    all_vuln_types.update(partial_by_type.keys())

    # Also count successes by type
    success_by_type = defaultdict(int)
    for success in successes:
        success_by_type[success['vuln_type']] += 1
    all_vuln_types.update(success_by_type.keys())

    for vuln_type in sorted(all_vuln_types):
        total = len(failures_by_type[vuln_type]) + len(partial_by_type[vuln_type]) + success_by_type[vuln_type]
        failed = len(failures_by_type[vuln_type])
        partial = len(partial_by_type[vuln_type])
        success = success_by_type[vuln_type]

        # Calculate success rate based on points
        total_points = (failed * 0) + (partial * 1) + (success * 2)
        max_points = total * 2
        success_rate = (total_points / max_points * 100) if max_points > 0 else 0

        print(f"{vuln_type:<35} {total:<8} {failed:<8} {partial:<8} {success:<8} {success_rate:>5.1f}%")

    print()
    print("=" * 140)
    print()

    # What types are hardest?
    print("HARDEST VULNERABILITY TYPES (Lowest Success Rate):")
    print()

    vuln_stats = []
    for vuln_type in all_vuln_types:
        total = len(failures_by_type[vuln_type]) + len(partial_by_type[vuln_type]) + success_by_type[vuln_type]
        failed = len(failures_by_type[vuln_type])
        partial = len(partial_by_type[vuln_type])
        success = success_by_type[vuln_type]

        total_points = (failed * 0) + (partial * 1) + (success * 2)
        max_points = total * 2
        success_rate = (total_points / max_points * 100) if max_points > 0 else 0

        if total > 0:
            vuln_stats.append((vuln_type, success_rate, total, failed, partial, success))

    vuln_stats.sort(key=lambda x: x[1])

    for i, (vuln_type, rate, total, failed, partial, success) in enumerate(vuln_stats[:10], 1):
        print(f"  {i}. {vuln_type:<35} {rate:>5.1f}% ({failed} failed, {partial} partial, {success} success)")

    print()
    print("=" * 140)

if __name__ == "__main__":
    analyze_codex_failures()
