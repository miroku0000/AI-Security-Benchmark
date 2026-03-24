#!/usr/bin/env python3
"""Analyze static analysis results across all models."""

import json
from pathlib import Path
from collections import Counter

def main():
    results_dir = Path("static_analyzer_results")

    all_model_stats = []
    vulnerability_by_model = {}

    for model_dir in sorted(results_dir.iterdir()):
        if not model_dir.is_dir():
            continue

        model_name = model_dir.name
        findings_file = model_dir / "deduplicated_combined_findings.json"

        if not findings_file.exists():
            continue

        with open(findings_file) as f:
            data = json.load(f)

        findings = data.get("findings", [])

        # Count by severity
        severity_counts = Counter(f.get("severity", "UNKNOWN") for f in findings)

        # Count by vulnerability type
        vuln_types = Counter(f.get("title", "Unknown") for f in findings)

        # Count by CWE
        cwe_counts = Counter()
        for f in findings:
            for cwe in f.get("cwe_ids", []):
                cwe_counts[cwe] += 1

        all_model_stats.append({
            "model": model_name,
            "total": len(findings),
            "high": severity_counts.get("HIGH", 0),
            "medium": severity_counts.get("MEDIUM", 0),
            "low": severity_counts.get("LOW", 0),
            "info": severity_counts.get("INFO", 0),
            "top_vulns": vuln_types.most_common(5)
        })

        vulnerability_by_model[model_name] = vuln_types

    # Sort by total findings
    all_model_stats.sort(key=lambda x: x["total"])

    print("=" * 80)
    print("STATIC ANALYSIS FINDINGS BY MODEL (Deduplicated)")
    print("=" * 80)
    print()

    print(f"{'Model':<30} {'Total':>8} {'HIGH':>6} {'MED':>6} {'LOW':>6} {'INFO':>6}")
    print("-" * 80)

    for stats in all_model_stats:
        print(f"{stats['model']:<30} {stats['total']:>8} {stats['high']:>6} "
              f"{stats['medium']:>6} {stats['low']:>6} {stats['info']:>6}")

    print()
    print("=" * 80)
    print("TOP 5 VULNERABILITY TYPES BY MODEL")
    print("=" * 80)

    for stats in all_model_stats[-5:]:  # Show top 5 models with most findings
        print(f"\n{stats['model']} ({stats['total']} total findings):")
        print("-" * 80)
        for vuln, count in stats['top_vulns']:
            short_name = vuln[:70] + "..." if len(vuln) > 70 else vuln
            print(f"  {count:>3}x {short_name}")

    # Find common vulnerabilities across all models
    print()
    print("=" * 80)
    print("MOST COMMON VULNERABILITIES (ACROSS ALL MODELS)")
    print("=" * 80)

    all_vulns = Counter()
    for vulns in vulnerability_by_model.values():
        all_vulns.update(vulns)

    for vuln, count in all_vulns.most_common(15):
        short_name = vuln[:65] + "..." if len(vuln) > 65 else vuln
        print(f"{count:>4}x {short_name}")

    print()
    print("=" * 80)
    print("KEY INSIGHTS")
    print("=" * 80)

    # Calculate averages
    total_findings = sum(s["total"] for s in all_model_stats)
    avg_findings = total_findings / len(all_model_stats)

    print(f"Total models analyzed: {len(all_model_stats)}")
    print(f"Total findings across all models: {total_findings}")
    print(f"Average findings per model: {avg_findings:.1f}")
    print(f"Model with most findings: {all_model_stats[-1]['model']} ({all_model_stats[-1]['total']})")
    print(f"Model with fewest findings: {all_model_stats[0]['model']} ({all_model_stats[0]['total']})")

    # HIGH severity analysis
    total_high = sum(s["high"] for s in all_model_stats)
    print(f"\nTotal HIGH severity findings: {total_high}")
    print(f"Average HIGH severity per model: {total_high / len(all_model_stats):.1f}")

    high_sorted = sorted(all_model_stats, key=lambda x: x["high"], reverse=True)
    print(f"\nModels with most HIGH severity issues:")
    for stats in high_sorted[:5]:
        print(f"  {stats['model']:<30} {stats['high']:>3} HIGH")

if __name__ == "__main__":
    main()
