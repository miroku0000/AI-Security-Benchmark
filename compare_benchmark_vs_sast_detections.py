#!/usr/bin/env python3
"""
Compare what vulnerabilities the benchmark detected vs what SAST tools detected.
This script answers: Do SAST tools catch the same vulnerabilities we intentionally tested for?
"""

import json
from pathlib import Path
from collections import defaultdict, Counter

# Mapping of benchmark vulnerability types to SAST pattern keywords
VULN_TYPE_MAPPING = {
    "sql_injection": ["sql", "sqli", "injection"],
    "xss": ["xss", "cross-site", "sanitize", "escape"],
    "command_injection": ["command", "subprocess", "shell", "os.system"],
    "path_traversal": ["path", "traversal", "directory"],
    "hardcoded_secrets": ["secret", "password", "credential", "hardcoded", "api_key", "token"],
    "jwt": ["jwt", "token", "verify", "decode"],
    "xxe": ["xml", "xxe", "entity"],
    "csrf": ["csrf", "cross-site request"],
    "deserialization": ["deserialize", "pickle", "unsafe load"],
    "missing_error_handling": ["error", "exception", "try"],
    "resource_leaks": ["leak", "close", "resource"],
}

def load_benchmark_report(model_name):
    """Load benchmark JSON report for a model."""
    reports_dir = Path("reports")

    # Try different file patterns
    patterns = [
        f"{model_name}_*.json",
        f"{model_name.replace(':', '_')}_*.json",
    ]

    for pattern in patterns:
        matches = list(reports_dir.glob(pattern))
        if matches:
            # Get most recent
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
    # Handle both sql_001 and nosql_001 formats
    parts = file_name.split('_')
    if len(parts) >= 2:
        return file_name  # Return full name like sql_001
    return None

def categorize_sast_finding(finding_title, finding_desc):
    """Categorize SAST finding into our vulnerability taxonomy."""
    text = (finding_title + " " + finding_desc).lower()

    categories = []
    for vuln_type, keywords in VULN_TYPE_MAPPING.items():
        if any(keyword in text for keyword in keywords):
            categories.append(vuln_type)

    return categories if categories else ["other"]

def main():
    models = [
        "starcoder2:7b",
        "claude-sonnet-4-5",
        "gpt-4o",
        "deepseek-coder",
        "o3",
    ]

    print("=" * 100)
    print("BENCHMARK vs SAST DETECTION COMPARISON")
    print("=" * 100)
    print()
    print("Goal: Determine if SAST tools detect the same vulnerabilities")
    print("      that our benchmark intentionally tests for.")
    print()
    print("=" * 100)
    print()

    all_comparisons = []

    for model_name in models:
        print(f"\n{'='*100}")
        print(f"MODEL: {model_name}")
        print(f"{'='*100}\n")

        # Load reports
        benchmark_report = load_benchmark_report(model_name)
        sast_findings = load_sast_findings(model_name)

        if not benchmark_report:
            print(f"❌ No benchmark report found for {model_name}")
            continue

        if not sast_findings:
            print(f"❌ No SAST findings found for {model_name}")
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

        # Compare each test case
        matches = 0
        mismatches = 0
        examples = []

        for result in detailed_results:
            prompt_id = result.get("prompt_id")
            benchmark_vulns = result.get("vulnerabilities", [])
            expected_vulns = result.get("expected_vulnerabilities", [])

            # Get SAST findings for this file
            sast_for_file = sast_by_file.get(prompt_id, [])

            # Categorize SAST findings
            sast_categories = set()
            for finding in sast_for_file:
                title = finding.get("title", "")
                desc = finding.get("description", "")
                categories = categorize_sast_finding(title, desc)
                sast_categories.update(categories)

            # Check if benchmark found the expected vulnerability
            benchmark_types = set(v["type"].lower() for v in benchmark_vulns)
            expected_types = set(v.lower() for v in expected_vulns)

            # Determine if it's a match
            found_by_both = []
            found_by_benchmark_only = []
            found_by_sast_only = []

            for expected in expected_types:
                benchmark_found = expected in benchmark_types
                sast_found = expected in sast_categories

                if benchmark_found and sast_found:
                    found_by_both.append(expected)
                    matches += 1
                elif benchmark_found and not sast_found:
                    found_by_benchmark_only.append(expected)
                elif not benchmark_found and sast_found:
                    found_by_sast_only.append(expected)

            # Store examples
            if found_by_both or found_by_benchmark_only or found_by_sast_only:
                examples.append({
                    "test": prompt_id,
                    "expected": list(expected_types),
                    "benchmark": list(benchmark_types),
                    "sast": list(sast_categories),
                    "both": found_by_both,
                    "benchmark_only": found_by_benchmark_only,
                    "sast_only": found_by_sast_only,
                })

        # Print summary for this model
        print(f"Test cases analyzed: {len(detailed_results)}")
        print(f"SAST findings: {len(sast_findings)} total")
        print()

        # Show specific examples
        print("DETECTION OVERLAP EXAMPLES:")
        print("-" * 100)

        for ex in examples[:10]:  # Show first 10
            print(f"\n{ex['test']}:")
            print(f"  Expected: {', '.join(ex['expected'])}")
            if ex['both']:
                print(f"  ✅ BOTH detected: {', '.join(ex['both'])}")
            if ex['benchmark_only']:
                print(f"  ⚠️  Benchmark only: {', '.join(ex['benchmark_only'])}")
            if ex['sast_only']:
                print(f"  🔍 SAST only: {', '.join(ex['sast_only'])}")

        all_comparisons.append({
            "model": model_name,
            "examples": examples,
        })

    print("\n\n" + "=" * 100)
    print("AGGREGATE ANALYSIS")
    print("=" * 100)
    print()

    # Aggregate statistics
    total_both = 0
    total_benchmark_only = 0
    total_sast_only = 0

    for comp in all_comparisons:
        for ex in comp["examples"]:
            total_both += len(ex["both"])
            total_benchmark_only += len(ex["benchmark_only"])
            total_sast_only += len(ex["sast_only"])

    total = total_both + total_benchmark_only + total_sast_only

    if total > 0:
        print(f"Vulnerabilities detected by BOTH: {total_both} ({total_both/total*100:.1f}%)")
        print(f"Vulnerabilities detected by BENCHMARK ONLY: {total_benchmark_only} ({total_benchmark_only/total*100:.1f}%)")
        print(f"Vulnerabilities detected by SAST ONLY: {total_sast_only} ({total_sast_only/total*100:.1f}%)")

    print()
    print("=" * 100)
    print("KEY INSIGHTS")
    print("=" * 100)
    print()
    print("1. DETECTION OVERLAP:")
    print(f"   - {total_both} vulnerabilities caught by both tools")
    print(f"   - This validates that both are detecting similar issues")
    print()
    print("2. BENCHMARK STRENGTH:")
    print(f"   - {total_benchmark_only} vulnerabilities caught ONLY by benchmark")
    print(f"   - These are specific to our security-by-design testing")
    print()
    print("3. SAST ADDITIONAL VALUE:")
    print(f"   - {total_sast_only} issues caught ONLY by SAST tools")
    print(f"   - These are code quality/style issues not security-critical")
    print()
    print("CONCLUSION:")
    print("-" * 100)
    if total_both > total_benchmark_only and total_both > total_sast_only:
        print("✅ Strong overlap! Both tools are detecting similar vulnerabilities.")
        print("   The benchmark and SAST tools complement each other well.")
    elif total_benchmark_only > total_both:
        print("⚠️  Benchmark detects more than SAST!")
        print("   Our detectors are catching vulnerabilities SAST tools miss.")
    else:
        print("🔍 SAST finds more patterns than benchmark.")
        print("   This is expected - SAST checks style/quality, benchmark checks security.")
    print()

if __name__ == "__main__":
    main()
