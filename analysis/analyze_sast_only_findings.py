#!/usr/bin/env python3
"""
Analyze findings that SAST tools caught but the benchmark missed.
Are these real security issues or just code quality noise?
"""

import json
from pathlib import Path
from collections import defaultdict

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
    print("SAST-ONLY FINDINGS ANALYSIS")
    print("=" * 100)
    print()
    print("Goal: Identify security issues that SAST caught but benchmark missed")
    print("      Are these real gaps in the benchmark or just noise?")
    print()
    print("=" * 100)
    print()

    all_sast_only = []

    for model_name in models:
        print(f"\n{'='*100}")
        print(f"MODEL: {model_name}")
        print(f"{'='*100}\n")

        # Load reports
        benchmark_report = load_benchmark_report(model_name)
        sast_findings = load_sast_findings(model_name)

        if not benchmark_report or not sast_findings:
            print(f"ERROR: Missing data for {model_name}")
            continue

        # Organize SAST findings by file
        sast_by_file = defaultdict(list)
        for finding in sast_findings:
            file_path = finding.get("file_path", "")
            file_id = extract_file_id(file_path)
            if file_id:
                sast_by_file[file_id].append(finding)

        # Get benchmark results
        detailed_results = benchmark_report.get("detailed_results", [])

        # Find SAST-only findings
        sast_only_findings = []

        for result in detailed_results:
            prompt_id = result.get("prompt_id")
            benchmark_vulns = result.get("vulnerabilities", [])
            score = result.get("score", 0)
            max_score = result.get("max_score", 0)

            # Get SAST findings for this file
            sast_for_file = sast_by_file.get(prompt_id, [])

            # Check if code is SECURE according to benchmark
            is_secure = score == max_score
            has_no_vulns = all(v["type"] == "SECURE" for v in benchmark_vulns)

            # If benchmark says secure but SAST found issues
            if (is_secure or has_no_vulns) and sast_for_file:
                for finding in sast_for_file:
                    sast_only_findings.append({
                        "test": prompt_id,
                        "severity": finding.get("severity", ""),
                        "rule": finding.get("rule_id", ""),
                        "title": finding.get("title", ""),
                        "description": finding.get("description", ""),
                        "line": finding.get("start_line", 0),
                        "tool": finding.get("tool_name", ""),
                        "benchmark_score": f"{score}/{max_score}",
                    })

        print(f"SAST-only findings: {len(sast_only_findings)}")
        print()

        if sast_only_findings:
            # Categorize by severity
            by_severity = defaultdict(list)
            for finding in sast_only_findings:
                by_severity[finding["severity"]].append(finding)

            print("BREAKDOWN BY SEVERITY:")
            print("-" * 100)
            for sev in ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]:
                if sev in by_severity:
                    print(f"{sev}: {len(by_severity[sev])} findings")

            print()

            # Show HIGH severity examples (potential real issues)
            high_sev = by_severity.get("HIGH", [])
            if high_sev:
                print(f"\nHIGH SEVERITY SAST-ONLY FINDINGS ({len(high_sev)} total):")
                print("-" * 100)
                for finding in high_sev[:10]:
                    print(f"\n{finding['test']} (line {finding['line']}):")
                    print(f"  Rule: {finding['rule']}")
                    print(f"  Title: {finding['title'][:80]}")
                    print(f"  Benchmark: {finding['benchmark_score']} (SECURE)")

            # Show MEDIUM severity examples
            medium_sev = by_severity.get("MEDIUM", [])
            if medium_sev:
                print(f"\n\nMEDIUM SEVERITY SAST-ONLY FINDINGS ({len(medium_sev)} total):")
                print("-" * 100)
                for finding in medium_sev[:5]:
                    print(f"\n{finding['test']} (line {finding['line']}):")
                    print(f"  Rule: {finding['rule']}")
                    print(f"  Title: {finding['title'][:80]}")

        all_sast_only.extend(sast_only_findings)

    # Aggregate analysis
    print("\n\n" + "=" * 100)
    print("AGGREGATE ANALYSIS")
    print("=" * 100)
    print()

    # Group by rule to find common patterns
    by_rule = defaultdict(list)
    for finding in all_sast_only:
        # Get primary rule ID
        rule = finding["rule"].split(",")[0].strip()
        by_rule[rule].append(finding)

    print("TOP SAST-ONLY RULES (Benchmark Gaps):")
    print("-" * 100)
    print(f"{'Rule':<15} {'Count':>6} {'Severity':<10} {'Example Title':<60}")
    print("-" * 100)

    for rule, findings in sorted(by_rule.items(), key=lambda x: len(x[1]), reverse=True)[:20]:
        sev = findings[0]["severity"]
        title = findings[0]["title"][:60]
        print(f"{rule:<15} {len(findings):>6} {sev:<10} {title}")

    print()
    print("=" * 100)
    print("CATEGORIZATION: Real Security Issues vs Noise")
    print("=" * 100)
    print()

    # Categorize findings
    real_security = []
    code_quality = []
    false_alarms = []

    for rule, findings in by_rule.items():
        sev = findings[0]["severity"]
        title = findings[0]["title"].lower()

        # Real security issues the benchmark should detect
        if any(keyword in title for keyword in [
            "sql injection", "command injection", "path traversal",
            "xss", "xxe", "ssrf", "deserialization", "crypto"
        ]) and sev in ["HIGH", "CRITICAL"]:
            real_security.extend(findings)

        # Code quality/style issues
        elif any(keyword in title for keyword in [
            "encoding", "maintainability", "complexity", "import",
            "best practice", "code style", "formatting"
        ]) or sev in ["INFO", "LOW"]:
            code_quality.extend(findings)

        # Likely false alarms (detected in secure code)
        else:
            false_alarms.extend(findings)

    print(f"REAL SECURITY ISSUES (benchmark should add): {len(real_security)}")
    print(f"CODE QUALITY/STYLE (not security): {len(code_quality)}")
    print(f"FALSE ALARMS (flagged secure code): {len(false_alarms)}")
    print()

    # Show real security issues
    if real_security:
        print("REAL SECURITY ISSUES MISSED BY BENCHMARK:")
        print("-" * 100)
        for finding in real_security[:15]:
            print(f"{finding['test']}: {finding['title'][:70]} ({finding['severity']})")

    print()
    print("=" * 100)
    print("RECOMMENDATIONS")
    print("=" * 100)
    print()

    if real_security:
        print(f"WARNING: BENCHMARK GAP: {len(real_security)} real security issues missed")
        print()
        print("Consider adding benchmark detectors for:")

        gap_categories = defaultdict(int)
        for finding in real_security:
            title = finding['title'].lower()
            if 'sql' in title:
                gap_categories['SQL Injection (advanced)'] += 1
            elif 'command' in title:
                gap_categories['Command Injection (advanced)'] += 1
            elif 'path' in title:
                gap_categories['Path Traversal (advanced)'] += 1
            elif 'deserial' in title:
                gap_categories['Deserialization (advanced)'] += 1
            else:
                gap_categories['Other'] += 1

        for cat, count in sorted(gap_categories.items(), key=lambda x: x[1], reverse=True):
            print(f"  - {cat}: {count} cases")
    else:
        print("PASS: NO SIGNIFICANT GAPS")
        print("   Benchmark catches all real security issues.")
        print("   SAST-only findings are mostly code quality/style.")

    print()

    if code_quality:
        print(f"INFO: CODE QUALITY: {len(code_quality)} style/quality issues")
        print("   These are not security vulnerabilities.")
        print("   Safe to ignore for security assessment.")

    print()
    print("=" * 100)
    print(f"TOTAL SAST-ONLY FINDINGS: {len(all_sast_only)}")
    print(f"  - Real security issues: {len(real_security)} ({len(real_security)/len(all_sast_only)*100:.1f}%)")
    print(f"  - Code quality: {len(code_quality)} ({len(code_quality)/len(all_sast_only)*100:.1f}%)")
    print(f"  - False alarms: {len(false_alarms)} ({len(false_alarms)/len(all_sast_only)*100:.1f}%)")
    print("=" * 100)
    print()

if __name__ == "__main__":
    main()
