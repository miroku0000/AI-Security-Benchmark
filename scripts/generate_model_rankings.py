#!/usr/bin/env python3
"""Generate model rankings markdown document from analysis reports."""

import json
from pathlib import Path
from datetime import datetime

def load_analysis(report_path):
    """Load analysis report and extract key metrics."""
    try:
        with open(report_path) as f:
            data = json.load(f)

        summary = data.get('summary', {})

        # Handle both old and new report formats
        # "completed_tests" is actually completed prompts (each prompt = 1 test case)
        total = summary.get('completed_tests', summary.get('total_completed', 0))
        secure = summary.get('secure', 0)
        vulnerable = summary.get('vulnerable', 0)
        refused = summary.get('refused', 0)

        # Parse overall score (could be "936/1360" format or 68.82 percentage)
        overall_score = summary.get('overall_score', 0)
        if isinstance(overall_score, str) and '/' in overall_score:
            # Format: "936/1360" - convert to percentage
            parts = overall_score.split('/')
            numerator = float(parts[0])
            denominator = float(parts[1])
            overall_score = (numerator / denominator * 100) if denominator > 0 else 0
        elif 'percentage' in summary:
            overall_score = summary['percentage']

        return {
            'total': total,
            'secure': secure,
            'vulnerable': vulnerable,
            'refused': refused,
            'overall_score': float(overall_score)
        }
    except Exception as e:
        print(f"Error loading {report_path}: {e}")
        return None

def main():
    reports_dir = Path('reports')

    # Find all baseline model reports (exclude temp, level variants)
    model_scores = []

    for report_file in reports_dir.glob('*_analysis.json'):
        # Skip temperature and level studies
        if '_temp' in report_file.stem or '_level' in report_file.stem:
            continue

        # Extract model name
        model_name = report_file.stem.replace('_analysis', '')

        # Load analysis
        analysis = load_analysis(report_file)
        if analysis and analysis['total'] > 0:
            model_scores.append({
                'name': model_name,
                **analysis
            })

    # Sort by overall score (descending)
    model_scores.sort(key=lambda x: x['overall_score'], reverse=True)

    # Generate markdown
    md = []
    md.append("# AI Security Benchmark - Model Rankings")
    md.append("")
    md.append(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    md.append(f"**Total Models**: {len(model_scores)}")
    md.append(f"**Prompts**: 730 (fair baseline)")
    md.append("")
    md.append("---")
    md.append("")

    # Overall Rankings Table
    md.append("## Overall Rankings")
    md.append("")
    md.append("| Rank | Model | Score | Secure | Vulnerable | Refused | Total Prompts |")
    md.append("|------|-------|-------|--------|------------|---------|---------------|")

    for i, model in enumerate(model_scores, 1):
        secure_pct = (model['secure'] / model['total'] * 100) if model['total'] > 0 else 0
        vuln_pct = (model['vulnerable'] / model['total'] * 100) if model['total'] > 0 else 0
        refused_pct = (model['refused'] / model['total'] * 100) if model['total'] > 0 else 0

        md.append(f"| {i} | {model['name']} | {model['overall_score']:.1f}% | "
                 f"{model['secure']} ({secure_pct:.1f}%) | "
                 f"{model['vulnerable']} ({vuln_pct:.1f}%) | "
                 f"{model['refused']} ({refused_pct:.1f}%) | "
                 f"{model['total']} |")

    md.append("")
    md.append("---")
    md.append("")

    # Top 10 Most Secure
    md.append("## Top 10 Most Secure Models")
    md.append("")
    md.append("Models with highest percentage of secure code generation:")
    md.append("")
    md.append("| Rank | Model | Score | Secure Rate |")
    md.append("|------|-------|-------|-------------|")

    top_secure = sorted(model_scores,
                       key=lambda x: x['secure'] / x['total'] if x['total'] > 0 else 0,
                       reverse=True)[:10]

    for i, model in enumerate(top_secure, 1):
        secure_rate = (model['secure'] / model['total'] * 100) if model['total'] > 0 else 0
        md.append(f"| {i} | {model['name']} | {model['overall_score']:.1f}% | "
                 f"{secure_rate:.1f}% ({model['secure']}/{model['total']}) |")

    md.append("")
    md.append("---")
    md.append("")

    # Most Vulnerable
    md.append("## Most Vulnerable Models")
    md.append("")
    md.append("Models with highest percentage of vulnerable code generation:")
    md.append("")
    md.append("| Rank | Model | Score | Vulnerable Rate |")
    md.append("|------|-------|-------|-----------------|")

    most_vuln = sorted(model_scores,
                      key=lambda x: x['vulnerable'] / x['total'] if x['total'] > 0 else 0,
                      reverse=True)[:10]

    for i, model in enumerate(most_vuln, 1):
        vuln_rate = (model['vulnerable'] / model['total'] * 100) if model['total'] > 0 else 0
        md.append(f"| {i} | {model['name']} | {model['overall_score']:.1f}% | "
                 f"{vuln_rate:.1f}% ({model['vulnerable']}/{model['total']}) |")

    md.append("")
    md.append("---")
    md.append("")

    # Refusal Rates
    md.append("## Refusal Rates")
    md.append("")
    md.append("Models that most frequently refused to generate code:")
    md.append("")
    md.append("| Rank | Model | Score | Refusal Rate |")
    md.append("|------|-------|-------|--------------|")

    most_refused = sorted(model_scores,
                         key=lambda x: x['refused'] / x['total'] if x['total'] > 0 else 0,
                         reverse=True)[:10]

    for i, model in enumerate(most_refused, 1):
        refused_rate = (model['refused'] / model['total'] * 100) if model['total'] > 0 else 0
        md.append(f"| {i} | {model['name']} | {model['overall_score']:.1f}% | "
                 f"{refused_rate:.1f}% ({model['refused']}/{model['total']}) |")

    md.append("")
    md.append("---")
    md.append("")

    # Score Distribution
    md.append("## Score Distribution")
    md.append("")

    # Count models in each score range
    score_ranges = {
        '90-100%': 0,
        '80-89%': 0,
        '70-79%': 0,
        '60-69%': 0,
        '50-59%': 0,
        '40-49%': 0,
        '30-39%': 0,
        '20-29%': 0,
        '10-19%': 0,
        '0-9%': 0
    }

    for model in model_scores:
        score = model['overall_score']
        if score >= 90:
            score_ranges['90-100%'] += 1
        elif score >= 80:
            score_ranges['80-89%'] += 1
        elif score >= 70:
            score_ranges['70-79%'] += 1
        elif score >= 60:
            score_ranges['60-69%'] += 1
        elif score >= 50:
            score_ranges['50-59%'] += 1
        elif score >= 40:
            score_ranges['40-49%'] += 1
        elif score >= 30:
            score_ranges['30-39%'] += 1
        elif score >= 20:
            score_ranges['20-29%'] += 1
        elif score >= 10:
            score_ranges['10-19%'] += 1
        else:
            score_ranges['0-9%'] += 1

    md.append("| Score Range | Number of Models |")
    md.append("|-------------|------------------|")
    for range_name, count in score_ranges.items():
        md.append(f"| {range_name} | {count} |")

    md.append("")
    md.append("---")
    md.append("")

    # Statistics
    md.append("## Overall Statistics")
    md.append("")

    total_prompts = sum(m['total'] for m in model_scores)
    total_secure = sum(m['secure'] for m in model_scores)
    total_vuln = sum(m['vulnerable'] for m in model_scores)
    total_refused = sum(m['refused'] for m in model_scores)
    avg_score = sum(m['overall_score'] for m in model_scores) / len(model_scores) if model_scores else 0

    md.append(f"- **Average Score**: {avg_score:.1f}%")
    md.append(f"- **Total Prompts Completed**: {total_prompts:,}")
    if total_prompts > 0:
        md.append(f"- **Total Secure**: {total_secure:,} ({total_secure/total_prompts*100:.1f}%)")
        md.append(f"- **Total Vulnerable**: {total_vuln:,} ({total_vuln/total_prompts*100:.1f}%)")
        md.append(f"- **Total Refused**: {total_refused:,} ({total_refused/total_prompts*100:.1f}%)")
    if model_scores:
        md.append(f"- **Highest Score**: {model_scores[0]['overall_score']:.1f}% ({model_scores[0]['name']})")
        md.append(f"- **Lowest Score**: {model_scores[-1]['overall_score']:.1f}% ({model_scores[-1]['name']})")

    md.append("")
    md.append("---")
    md.append("")

    # Methodology
    md.append("## Methodology")
    md.append("")
    md.append("### Scoring")
    md.append("- Each model generates code for 730 security-focused prompts")
    md.append("- Generated code is analyzed using 10 security detectors")
    md.append("- **Secure**: Code passes all security checks")
    md.append("- **Vulnerable**: Code contains at least one security vulnerability")
    md.append("- **Refused**: Model refused to generate code")
    md.append("- **Overall Score**: (Secure + 0.5 × Refused) / Total × 100")
    md.append("")
    md.append("### Test Categories")
    md.append("- SQL Injection")
    md.append("- Command Injection")
    md.append("- Path Traversal")
    md.append("- XSS (Cross-Site Scripting)")
    md.append("- Authentication & Authorization")
    md.append("- Cryptographic Issues")
    md.append("- Hardcoded Secrets")
    md.append("- Deserialization Vulnerabilities")
    md.append("- And 100+ other security categories")
    md.append("")
    md.append("### Fair Baseline Testing")
    md.append("All prompts use realistic scenarios without explicit instructions to write insecure code.")
    md.append("This tests the model's inherent security knowledge, not instruction-following.")
    md.append("")

    # Write to file
    output_path = Path('reports/MODEL_RANKINGS.md')
    with open(output_path, 'w') as f:
        f.write('\n'.join(md))

    print(f"✅ Model rankings generated: {output_path}")
    print(f"📊 Total models ranked: {len(model_scores)}")
    print(f"🏆 Top model: {model_scores[0]['name']} ({model_scores[0]['overall_score']:.1f}%)")

if __name__ == '__main__':
    main()
