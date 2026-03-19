#!/usr/bin/env python3
"""Compare benchmark performance vs SAST findings."""

import json
from pathlib import Path

# Benchmark scores from COMPREHENSIVE_RESULTS_208POINT.md
benchmark_scores = {
    "starcoder2:7b": {"score": 180, "pct": 86.5, "secure": 51, "vulnerable": 7},
    "starcoder2": {"score": 146, "pct": 70.2, "secure": 40, "vulnerable": 12},
    "gpt-5.2": {"score": 144, "pct": 69.2, "secure": 34, "vulnerable": 14},
    "deepseek-coder": {"score": 136, "pct": 65.4, "secure": 32, "vulnerable": 16},
    "o3": {"score": 117, "pct": 56.2, "secure": 23, "vulnerable": 23},
    "codellama": {"score": 115, "pct": 55.3, "secure": 19, "vulnerable": 29},
    "codegemma:7b-instruct": {"score": 113, "pct": 54.3, "secure": 25, "vulnerable": 26},
    "deepseek-coder:6.7b-instruct": {"score": 108, "pct": 51.9, "secure": 20, "vulnerable": 26},
    "gpt-4": {"score": 105, "pct": 50.5, "secure": 21, "vulnerable": 26},
    "o3-mini": {"score": 104, "pct": 50.0, "secure": 18, "vulnerable": 29},
    "mistral": {"score": 104, "pct": 50.0, "secure": 16, "vulnerable": 30},
    "llama3.1": {"score": 100, "pct": 48.1, "secure": 14, "vulnerable": 27},
    "o1": {"score": 100, "pct": 48.1, "secure": 16, "vulnerable": 30},
    "codegemma": {"score": 100, "pct": 48.1, "secure": 19, "vulnerable": 30},
    "gpt-4o": {"score": 93, "pct": 44.7, "secure": 17, "vulnerable": 33},
    "claude-sonnet-4-5": {"score": 92, "pct": 44.2, "secure": 16, "vulnerable": 29},  # old version
    "gpt-4o-mini": {"score": 90, "pct": 43.3, "secure": 15, "vulnerable": 32},
    "qwen2.5-coder:14b": {"score": 90, "pct": 43.3, "secure": 15, "vulnerable": 31},
    "gpt-3.5-turbo": {"score": 87, "pct": 41.8, "secure": 17, "vulnerable": 35},
    "qwen2.5-coder": {"score": 86, "pct": 41.4, "secure": 12, "vulnerable": 36},
}

def main():
    results_dir = Path("static_analyzer_results")

    comparison = []

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
        high = sum(1 for f in findings if f.get("severity") == "HIGH")
        medium = sum(1 for f in findings if f.get("severity") == "MEDIUM")
        low = sum(1 for f in findings if f.get("severity") == "LOW")
        info = sum(1 for f in findings if f.get("severity") == "INFO")

        # Get benchmark score if available
        bench = benchmark_scores.get(model_name, {})

        comparison.append({
            "model": model_name,
            "bench_score": bench.get("score", 0),
            "bench_pct": bench.get("pct", 0),
            "bench_secure": bench.get("secure", 0),
            "bench_vuln": bench.get("vulnerable", 0),
            "sast_total": len(findings),
            "sast_high": high,
            "sast_medium": medium,
            "sast_low": low,
            "sast_info": info,
        })

    # Sort by benchmark score
    comparison.sort(key=lambda x: x["bench_score"], reverse=True)

    print("=" * 100)
    print("BENCHMARK PERFORMANCE vs SAST FINDINGS")
    print("=" * 100)
    print()
    print("Question: Do models that write more secure code (high benchmark score)")
    print("          also generate code with fewer SAST findings?")
    print()
    print("=" * 100)
    print()

    print(f"{'Model':<30} {'Bench':>6} {'Secure':>6} {'Vuln':>5} | {'SAST':>5} {'HIGH':>5} {'MED':>4} {'LOW':>4}")
    print("-" * 100)

    for item in comparison:
        if item["bench_score"] == 0:
            continue

        print(f"{item['model']:<30} {item['bench_score']:>6} {item['bench_secure']:>6} "
              f"{item['bench_vuln']:>5} | {item['sast_total']:>5} {item['sast_high']:>5} "
              f"{item['sast_medium']:>4} {item['sast_low']:>4}")

    print()
    print("=" * 100)
    print("CORRELATION ANALYSIS")
    print("=" * 100)
    print()

    # Analyze correlation
    valid_items = [x for x in comparison if x["bench_score"] > 0]

    # Top 5 benchmark performers vs SAST findings
    print("Top 5 Benchmark Performers:")
    print("-" * 100)
    for item in valid_items[:5]:
        print(f"  {item['model']:<28} Bench: {item['bench_pct']:>5.1f}%  |  "
              f"SAST Total: {item['sast_total']:>3}  (HIGH: {item['sast_high']:>2})")

    print()
    print("Bottom 5 Benchmark Performers:")
    print("-" * 100)
    for item in valid_items[-5:]:
        print(f"  {item['model']:<28} Bench: {item['bench_pct']:>5.1f}%  |  "
              f"SAST Total: {item['sast_total']:>3}  (HIGH: {item['sast_high']:>2})")

    print()
    print("=" * 100)
    print("KEY INSIGHTS")
    print("=" * 100)
    print()

    # Calculate averages
    top5 = valid_items[:5]
    bottom5 = valid_items[-5:]

    top5_avg_sast = sum(x["sast_total"] for x in top5) / len(top5)
    bottom5_avg_sast = sum(x["sast_total"] for x in bottom5) / len(bottom5)

    top5_avg_high = sum(x["sast_high"] for x in top5) / len(top5)
    bottom5_avg_high = sum(x["sast_high"] for x in bottom5) / len(bottom5)

    print(f"Top 5 models (by benchmark):")
    print(f"  Average benchmark score: {sum(x['bench_pct'] for x in top5) / len(top5):.1f}%")
    print(f"  Average SAST findings: {top5_avg_sast:.1f}")
    print(f"  Average HIGH severity: {top5_avg_high:.1f}")
    print()
    print(f"Bottom 5 models (by benchmark):")
    print(f"  Average benchmark score: {sum(x['bench_pct'] for x in bottom5) / len(bottom5):.1f}%")
    print(f"  Average SAST findings: {bottom5_avg_sast:.1f}")
    print(f"  Average HIGH severity: {bottom5_avg_high:.1f}")
    print()

    # The paradox
    print("INFO: THE PARADOX:")
    print("-" * 100)

    if top5_avg_sast < bottom5_avg_sast:
        print(f"PASS: Top performers have FEWER SAST findings ({top5_avg_sast:.1f} vs {bottom5_avg_sast:.1f})")
        print("   This suggests high-performing models write cleaner, simpler code.")
    else:
        print(f"WARNING: Top performers have MORE SAST findings ({top5_avg_sast:.1f} vs {bottom5_avg_sast:.1f})")
        print("   This is counterintuitive!")

    print()
    print("Possible explanations:")
    print("  1. SAST tools detect patterns, not actual vulnerabilities")
    print("  2. Top performers may generate more verbose/complete code (more to scan)")
    print("  3. Bottom performers might generate simpler/incomplete code (less to detect)")
    print("  4. SAST findings include style/quality issues, not just security")
    print("  5. The benchmark measures intent (secure-by-design), SAST measures code patterns")
    print()

    # Specific example
    print("=" * 100)
    print("SPECIFIC EXAMPLE: starcoder2:7b (The Winner)")
    print("=" * 100)
    print()
    winner = valid_items[0]
    print(f"Model: {winner['model']}")
    print(f"  Benchmark Score: {winner['bench_score']}/208 ({winner['bench_pct']:.1f}%)")
    print(f"  Secure implementations: {winner['bench_secure']}/66")
    print(f"  Vulnerable implementations: {winner['bench_vuln']}/66")
    print()
    print(f"  SAST Findings: {winner['sast_total']}")
    print(f"    HIGH severity: {winner['sast_high']}")
    print(f"    MEDIUM severity: {winner['sast_medium']}")
    print(f"    LOW severity: {winner['sast_low']}")
    print(f"    INFO severity: {winner['sast_info']}")
    print()
    print("Interpretation:")
    print("  Despite being the BEST performer in security (86.5%), it still has")
    print(f"  {winner['sast_total']} SAST findings. This shows that SAST tools flag patterns")
    print("  that may not represent actual exploitable vulnerabilities.")
    print()

if __name__ == "__main__":
    main()
