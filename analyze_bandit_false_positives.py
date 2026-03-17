#!/usr/bin/env python3
"""
Analyze Bandit false positives by comparing with benchmark ground truth.
"""

import json
from pathlib import Path
from collections import defaultdict, Counter

def load_benchmark_report(model_name):
    """Load benchmark JSON report for a model."""
    reports_dir = Path("reports")

    patterns = [
        f"{model_name}_*.json",
        f"{model_name.replace(':', '_')}_*.json",
        f"{model_name}-old_*.json",
    ]

    for pattern in patterns:
        matches = list(reports_dir.glob(pattern))
        if matches:
            report_file = sorted(matches)[-1]
            with open(report_file) as f:
                return json.load(f)

    return None

def load_sast_findings(model_name):
    """Load SAST findings for a model."""
    sast_dir = Path("static_analyzer_results") / model_name
    findings_file = sast_dir / "deduplicated_combined_findings.json"

    if not findings_file.exists():
        return None

    with open(findings_file) as f:
        data = json.load(f)
        return data.get("findings", [])

def extract_file_id(file_path):
    """Extract test ID from file path (e.g., sql_001, xss_002)."""
    file_name = Path(file_path).stem
    return file_name

def main():
    models = [
        "starcoder2:7b",
        "claude-sonnet-4-5",
        "gpt-4o",
        "deepseek-coder",
    ]

    print("=" * 100)
    print("BANDIT FALSE POSITIVE ANALYSIS")
    print("=" * 100)
    print()
    print("Compares Bandit findings against benchmark ground truth to identify")
    print("false positives, true positives, and missed vulnerabilities.")
    print()
    print("=" * 100)
    print()

    all_stats = []

    for model_name in models:
        print(f"\n{'='*100}")
        print(f"MODEL: {model_name}")
        print(f"{'='*100}\n")

        # Load reports
        benchmark_report = load_benchmark_report(model_name)
        sast_findings = load_sast_findings(model_name)

        if not benchmark_report or not sast_findings:
            print(f"❌ Missing data for {model_name}")
            continue

        # Extract Bandit findings only
        bandit_findings = [
            f for f in sast_findings
            if "bandit" in f.get("tool_name", "").lower()
        ]

        print(f"Total Bandit findings: {len(bandit_findings)}")
        print()

        # Organize by file and rule
        findings_by_file = defaultdict(list)
        for finding in bandit_findings:
            file_path = finding.get("file_path", "")
            file_id = extract_file_id(file_path)
            findings_by_file[file_id].append(finding)

        # Get benchmark results
        detailed_results = benchmark_report.get("detailed_results", [])

        # Categorize findings
        true_positives = []
        false_positives = []
        missed_by_bandit = []

        for result in detailed_results:
            prompt_id = result.get("prompt_id")
            benchmark_vulns = result.get("vulnerabilities", [])
            expected_vulns = result.get("expected_vulnerabilities", [])
            score = result.get("score", 0)
            max_score = result.get("max_score", 0)

            # Get Bandit findings for this file
            bandit_for_file = findings_by_file.get(prompt_id, [])

            # Determine if code is vulnerable according to benchmark
            is_vulnerable = score < max_score
            has_vulns = len([v for v in benchmark_vulns if v["type"] != "SECURE"]) > 0

            # Categorize Bandit findings
            for finding in bandit_for_file:
                rule_id = finding.get("rule_id", "")
                severity = finding.get("severity", "")
                title = finding.get("title", "")

                # Check if this is a true positive
                # True positive: Bandit found something AND benchmark found a real vuln
                if has_vulns:
                    true_positives.append({
                        "test": prompt_id,
                        "rule": rule_id,
                        "severity": severity,
                        "title": title,
                        "benchmark_score": f"{score}/{max_score}",
                    })
                else:
                    # False positive: Bandit flagged but code is secure
                    false_positives.append({
                        "test": prompt_id,
                        "rule": rule_id,
                        "severity": severity,
                        "title": title,
                        "benchmark_score": f"{score}/{max_score}",
                    })

            # Check if Bandit missed a vulnerability
            if has_vulns and not bandit_for_file:
                vuln_types = [v["type"] for v in benchmark_vulns if v["type"] != "SECURE"]
                missed_by_bandit.append({
                    "test": prompt_id,
                    "vulnerabilities": vuln_types,
                    "benchmark_score": f"{score}/{max_score}",
                })

        # Print statistics
        print(f"TRUE POSITIVES: {len(true_positives)}")
        print(f"FALSE POSITIVES: {len(false_positives)}")
        print(f"MISSED BY BANDIT: {len(missed_by_bandit)}")
        print()

        # Show false positive examples
        if false_positives:
            print("FALSE POSITIVE EXAMPLES:")
            print("-" * 100)

            # Group by rule
            fp_by_rule = defaultdict(list)
            for fp in false_positives:
                rule = fp["rule"].split(",")[0]  # Get first rule ID
                fp_by_rule[rule].append(fp)

            for rule, fps in sorted(fp_by_rule.items(), key=lambda x: len(x[1]), reverse=True):
                print(f"\n{rule}: {len(fps)} false positives")
                for fp in fps[:3]:  # Show first 3
                    print(f"  - {fp['test']} ({fp['severity']}): {fp['title'][:70]}")

        print()

        # Show missed vulnerabilities
        if missed_by_bandit:
            print("MISSED BY BANDIT (Top 10):")
            print("-" * 100)
            for missed in missed_by_bandit[:10]:
                print(f"  {missed['test']}: {', '.join(missed['vulnerabilities'])}")

        # Calculate stats
        total_bandit = len(bandit_findings)
        tp_rate = len(true_positives) / total_bandit * 100 if total_bandit > 0 else 0
        fp_rate = len(false_positives) / total_bandit * 100 if total_bandit > 0 else 0

        all_stats.append({
            "model": model_name,
            "total_bandit": total_bandit,
            "true_positives": len(true_positives),
            "false_positives": len(false_positives),
            "missed": len(missed_by_bandit),
            "tp_rate": tp_rate,
            "fp_rate": fp_rate,
        })

    # Aggregate statistics
    print("\n\n" + "=" * 100)
    print("AGGREGATE STATISTICS")
    print("=" * 100)
    print()

    print(f"{'Model':<25} {'Total':>7} {'TP':>5} {'FP':>5} {'Missed':>7} {'TP%':>6} {'FP%':>6}")
    print("-" * 100)

    for stats in all_stats:
        print(f"{stats['model']:<25} {stats['total_bandit']:>7} {stats['true_positives']:>5} "
              f"{stats['false_positives']:>5} {stats['missed']:>7} "
              f"{stats['tp_rate']:>5.1f}% {stats['fp_rate']:>5.1f}%")

    # Overall averages
    if all_stats:
        avg_tp_rate = sum(s['tp_rate'] for s in all_stats) / len(all_stats)
        avg_fp_rate = sum(s['fp_rate'] for s in all_stats) / len(all_stats)
        total_tp = sum(s['true_positives'] for s in all_stats)
        total_fp = sum(s['false_positives'] for s in all_stats)
        total_missed = sum(s['missed'] for s in all_stats)

        print()
        print(f"AVERAGE TRUE POSITIVE RATE: {avg_tp_rate:.1f}%")
        print(f"AVERAGE FALSE POSITIVE RATE: {avg_fp_rate:.1f}%")
        print()
        print(f"TOTAL TRUE POSITIVES: {total_tp}")
        print(f"TOTAL FALSE POSITIVES: {total_fp}")
        print(f"TOTAL MISSED: {total_missed}")

    print()
    print("=" * 100)
    print("KEY INSIGHTS")
    print("=" * 100)
    print()

    if avg_fp_rate > 50:
        print(f"⚠️  HIGH FALSE POSITIVE RATE ({avg_fp_rate:.1f}%)")
        print("   Bandit flags many secure code patterns as vulnerabilities.")
        print("   Most findings require manual review to confirm exploitability.")
    elif avg_fp_rate > 25:
        print(f"⚠️  MODERATE FALSE POSITIVE RATE ({avg_fp_rate:.1f}%)")
        print("   About 1 in 4 Bandit findings are false alarms.")
    else:
        print(f"✅ LOW FALSE POSITIVE RATE ({avg_fp_rate:.1f}%)")
        print("   Bandit findings are generally accurate.")

    print()

    if avg_tp_rate < 50:
        print(f"⚠️  LOW TRUE POSITIVE RATE ({avg_tp_rate:.1f}%)")
        print("   Bandit misses more vulnerabilities than it catches.")
    else:
        print(f"✅ GOOD TRUE POSITIVE RATE ({avg_tp_rate:.1f}%)")
        print("   Bandit catches most obvious vulnerabilities.")

    print()
    print("COMMON FALSE POSITIVE PATTERNS:")
    print("-" * 100)
    print("1. B201 (debug=True) - Flags test code in if __name__ == '__main__'")
    print("2. B105 (hardcoded passwords) - Flags placeholder values in comments")
    print("3. B110 (try/except/pass) - Flags intentional error suppression")
    print("4. B404/B403 (import warnings) - Flags legitimate library usage")
    print()

if __name__ == "__main__":
    main()
