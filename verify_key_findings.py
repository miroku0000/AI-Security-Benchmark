#!/usr/bin/env python3
"""
Verify and update key findings from the benchmark study
"""
import json
from pathlib import Path
from collections import defaultdict

def analyze_findings():
    reports_dir = Path('reports')

    print("=" * 80)
    print("KEY FINDINGS VERIFICATION - UPDATED DATA")
    print("=" * 80)
    print()

    # Finding 1: Best model performance
    print("FINDING 1: No model achieves 100% security")
    print("-" * 80)

    report_file = reports_dir / 'codex-app-security-skill.json'
    with open(report_file) as f:
        data = json.load(f)

    summary = data.get('summary', {})
    total_prompts = summary.get('total_prompts', 0)
    completed = summary.get('completed_tests', 0)

    vulnerable_count = 0
    secure_count = 0

    for result in data.get('detailed_results', []):
        primary = result.get('primary_detector_result', '')
        if primary == 'FAIL':
            vulnerable_count += 1
        elif primary == 'PASS':
            secure_count += 1

    percentage = (secure_count / completed * 100) if completed > 0 else 0

    print(f"✓ Best configuration (codex-app-security-skill): {percentage:.1f}%")
    print(f"  Secure: {secure_count}")
    print(f"  Vulnerable: {vulnerable_count}")
    print(f"  Total tests: {completed}")
    print(f"  Finding: Even the best model produces {vulnerable_count} exploitable vulnerabilities")
    print()

    # Finding 2: Claude Code improvement
    print("FINDING 2: Wrapper engineering effectiveness")
    print("-" * 80)

    claude_code_file = reports_dir / 'claude-code.json'
    claude_opus_file = reports_dir / 'claude-opus-4-6.json'

    with open(claude_code_file) as f:
        claude_code_data = json.load(f)
    with open(claude_opus_file) as f:
        claude_opus_data = json.load(f)

    claude_code_pct = claude_code_data['summary']['percentage']
    claude_opus_pct = claude_opus_data['summary']['percentage']

    improvement = claude_code_pct - claude_opus_pct

    print(f"✓ Claude Code: {claude_code_pct:.1f}%")
    print(f"✓ Claude Opus 4.6: {claude_opus_pct:.1f}%")
    print(f"✓ Improvement: {improvement:.1f} percentage points")
    print(f"  (OLD: 7.3pp → NEW: {improvement:.1f}pp)")
    print()

    # Finding 3: Temperature effect
    print("FINDING 3: Temperature effect on security")
    print("-" * 80)

    temp_models = ['claude-sonnet-4-5', 'starcoder2', 'codellama', 'deepseek-coder']
    temps = ['0.0', '0.5', '0.7', '1.0']

    max_range = 0
    max_model = None

    for model in temp_models:
        scores = []
        for temp in temps:
            report_file = reports_dir / f'{model}_temp{temp}.json'
            if report_file.exists():
                with open(report_file) as f:
                    data = json.load(f)
                    pct = data['summary']['percentage']
                    scores.append(pct)

        if scores:
            temp_range = max(scores) - min(scores)
            if temp_range > max_range:
                max_range = temp_range
                max_model = model

    print(f"✓ Maximum temperature effect: {max_range:.1f} percentage points")
    print(f"  Model: {max_model}")
    print(f"  (OLD: 3.4pp → NEW: {max_range:.1f}pp)")
    print()

    # Finding 4: Infrastructure-as-Code security
    print("FINDING 4: Infrastructure-as-Code security")
    print("-" * 80)

    # Analyze IaC categories
    iac_categories = [
        'cloud_iam_misconfiguration',
        'cloud_network_security',
        'cloud_database_security',
        'cloud_storage_security',
        'cloud_compute_security',
        'container_security',
        'cicd_security',
        'serverless_security'
    ]

    # Sample from one model to get category breakdown
    report_file = reports_dir / 'gpt-4o.json'
    with open(report_file) as f:
        data = json.load(f)

    iac_scores = []
    non_iac_scores = []

    for result in data.get('detailed_results', []):
        category = result.get('category', '')
        score = result.get('score', 0)
        max_score = result.get('max_score', 2)

        if max_score > 0:
            pct = (score / max_score * 100)
            if category in iac_categories:
                iac_scores.append(pct)
            else:
                non_iac_scores.append(pct)

    iac_avg = sum(iac_scores) / len(iac_scores) if iac_scores else 0
    non_iac_avg = sum(non_iac_scores) / len(non_iac_scores) if non_iac_scores else 0
    gap = non_iac_avg - iac_avg

    print(f"✓ IaC average security: {iac_avg:.1f}%")
    print(f"✓ Non-IaC average security: {non_iac_avg:.1f}%")
    print(f"✓ Security gap: {gap:.1f} percentage points")
    print(f"  (IaC is {gap:.1f}pp LESS secure than typical code)")
    print()

    # Finding 5: Language comparison
    print("FINDING 5: Language vulnerability rates")
    print("-" * 80)

    # Aggregate across multiple models
    language_stats = defaultdict(lambda: {'total': 0, 'vulnerable': 0})

    base_models = ['gpt-4o', 'claude-sonnet-4-5', 'deepseek-coder', 'starcoder2']

    for model in base_models:
        report_file = reports_dir / f'{model}.json'
        if report_file.exists():
            with open(report_file) as f:
                data = json.load(f)

            for result in data.get('detailed_results', []):
                lang = result.get('language', 'unknown')
                primary = result.get('primary_detector_result', '')

                language_stats[lang]['total'] += 1
                if primary == 'FAIL':
                    language_stats[lang]['vulnerable'] += 1

    # Calculate percentages
    lang_vuln_rates = {}
    for lang, stats in language_stats.items():
        if stats['total'] > 10:  # Only languages with enough samples
            vuln_rate = (stats['vulnerable'] / stats['total'] * 100)
            lang_vuln_rates[lang] = vuln_rate

    print("Language vulnerability rates (% of code that is vulnerable):")
    for lang in ['rust', 'go', 'python', 'javascript']:
        if lang in lang_vuln_rates:
            print(f"  {lang.capitalize()}: {lang_vuln_rates[lang]:.1f}% vulnerable")

    if 'rust' in lang_vuln_rates and 'python' in lang_vuln_rates:
        rust_python_gap = lang_vuln_rates['python'] - lang_vuln_rates['rust']
        print(f"\n  Gap (Python vs Rust): {rust_python_gap:.1f} percentage points")

    if 'go' in lang_vuln_rates and 'javascript' in lang_vuln_rates:
        go_js_gap = lang_vuln_rates['javascript'] - lang_vuln_rates['go']
        print(f"  Gap (JavaScript vs Go): {go_js_gap:.1f} percentage points")
    print()

    # Finding 6: Level study effectiveness
    print("FINDING 6: Security prompting effectiveness by provider")
    print("-" * 80)

    level_studies = {
        'claude-opus-4-6': 'Anthropic',
        'claude-sonnet-4-5': 'Anthropic',
        'gpt-4o': 'OpenAI',
        'gpt-4o-mini': 'OpenAI',
        'deepseek-coder': 'Ollama',
        'llama3.1': 'Ollama',
    }

    for model, provider in level_studies.items():
        base_file = reports_dir / f'{model}.json'
        level5_file = reports_dir / f'{model}_level5.json'

        if base_file.exists() and level5_file.exists():
            with open(base_file) as f:
                base_data = json.load(f)
            with open(level5_file) as f:
                level5_data = json.load(f)

            base_pct = base_data['summary']['percentage']
            level5_pct = level5_data['summary']['percentage']
            improvement = level5_pct - base_pct

            print(f"  {model} ({provider}): {base_pct:.1f}% → {level5_pct:.1f}% ({improvement:+.1f}pp)")

    print()
    print("=" * 80)

if __name__ == '__main__':
    analyze_findings()
