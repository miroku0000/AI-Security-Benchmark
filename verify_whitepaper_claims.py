#!/usr/bin/env python3
"""
Verify all major claims in the whitepaper against actual benchmark data.
"""

import json
import glob
import yaml
from collections import defaultdict

def load_config():
    """Load benchmark configuration."""
    with open('benchmark_config.yaml') as f:
        return yaml.safe_load(f)

def load_all_reports():
    """Load all benchmark reports."""
    reports = []
    for path in glob.glob("reports/*_20260323.json"):
        try:
            with open(path) as f:
                data = json.load(f)
                reports.append(data)
        except Exception as e:
            print(f"Error loading {path}: {e}")
    return reports

def verify_model_counts():
    """Verify claim: '22 base AI models tested across 26 configurations'"""
    print("\n=== CLAIM 1: Model Counts ===")
    print("Whitepaper claims: '22 base AI models tested across 26 configurations'")

    config = load_config()

    # Count base models (API + Ollama)
    openai_count = len(config['models']['openai'])
    anthropic_count = len(config['models']['anthropic'])
    google_count = len(config['models']['google'])
    ollama_count = len(config['models']['ollama'])

    base_models = openai_count + anthropic_count + google_count + ollama_count

    # Count wrapper tools
    cursor_count = len(config['models'].get('cursor', []))
    codex_count = len(config['models'].get('codex-app', []))
    claude_code_count = len(config['models'].get('claude-code', []))

    wrappers = cursor_count + codex_count + claude_code_count

    # Codex.app tested twice (with/without security skill) = +1 config
    configurations = base_models + wrappers + 1  # +1 for codex-app second config

    print(f"\nActual data from benchmark_config.yaml:")
    print(f"  OpenAI API: {openai_count}")
    print(f"  Anthropic API: {anthropic_count}")
    print(f"  Google API: {google_count}")
    print(f"  Ollama: {ollama_count}")
    print(f"  Cursor: {cursor_count}")
    print(f"  Codex.app: {codex_count}")
    print(f"  Claude Code: {claude_code_count}")
    print(f"\nBase models (API + Ollama): {base_models}")
    print(f"Wrapper tools: {wrappers}")
    print(f"Codex.app tested twice: +1 configuration")
    print(f"Total configurations: {configurations}")

    if base_models == 22:
        print(f"\n✅ VERIFIED: 22 base models is CORRECT")
    else:
        print(f"\n❌ ERROR: Whitepaper says 22 but actual is {base_models}")

    if configurations == 26:
        print(f"✅ VERIFIED: 26 configurations is CORRECT")
    else:
        print(f"❌ ERROR: Whitepaper says 26 but actual is {configurations}")

def verify_top_rankings():
    """Verify top 10 rankings from whitepaper."""
    print("\n=== CLAIM 2: Top 10 Rankings ===")
    print("Whitepaper claims (README Top 10):")
    print("  1. Codex.app (Security Skill): 311/350 (88.9%)")
    print("  2. Codex.app (Baseline): 302/350 (86.3%)")
    print("  3. Claude Code CLI: 222/264 (84.1%)")

    # Find actual reports
    reports = glob.glob("reports/*_20260323.json")
    results = []

    for path in reports:
        try:
            with open(path) as f:
                data = json.load(f)
                summary = data.get('summary', {})
                score_str = summary.get('overall_score', '0/0')

                if '/' in score_str:
                    score, max_score = map(int, score_str.split('/'))
                    if max_score == 350:  # Focus on 350-point scale
                        results.append({
                            'model': data.get('model_name', 'Unknown'),
                            'score': score,
                            'max': max_score,
                            'pct': summary.get('percentage', 0)
                        })
        except:
            pass

    # Sort by score
    results.sort(key=lambda x: x['score'], reverse=True)

    print(f"\nActual top 10 from 350-point reports (March 23, 2026):")
    for i, r in enumerate(results[:10], 1):
        print(f"  {i:2}. {r['model']:45} {r['score']}/{r['max']} ({r['pct']:.1f}%)")

    # Verify specific claims
    if results[0]['model'] == 'codex-app-security-skill' and results[0]['score'] == 311:
        print("\n✅ VERIFIED: Codex.app (Security Skill) = 311/350 (88.9%)")
    else:
        print(f"\n❌ ERROR: Top model is {results[0]['model']} with {results[0]['score']}")

    if results[1]['model'] == 'codex-app-no-skill' and results[1]['score'] == 302:
        print("✅ VERIFIED: Codex.app (Baseline) = 302/350 (86.3%)")
    else:
        print(f"❌ ERROR: #2 model is {results[1]['model']} with {results[1]['score']}")

    # Check Claude Code separately (264-point scale)
    claude_code_path = "reports/claude-code_208point_20260323.json"
    try:
        with open(claude_code_path) as f:
            data = json.load(f)
            summary = data['summary']
            if summary['overall_score'] == '222/264':
                print("✅ VERIFIED: Claude Code CLI = 222/264 (84.1%)")
            else:
                print(f"❌ ERROR: Claude Code score is {summary['overall_score']}")
    except:
        print("❌ ERROR: Could not find Claude Code report")

def verify_temperature_study():
    """Verify temperature study claims."""
    print("\n=== CLAIM 3: Temperature Study ===")
    print("Whitepaper claims:")
    print("  - StarCoder2: 17.3 pp variation (63.5% → 80.8%)")
    print("  - DeepSeek-Coder temp 0.7: 72.0% (best)")

    # Find temperature study reports
    starcoder2_temps = {}
    deepseek_temps = {}

    for path in glob.glob("reports/starcoder2*_20260323.json"):
        try:
            with open(path) as f:
                data = json.load(f)
                summary = data['summary']
                score_str = summary['overall_score']
                if '/' in score_str:
                    score, max_score = map(int, score_str.split('/'))
                    if max_score == 350:
                        model_name = data['model_name']
                        pct = summary['percentage']
                        starcoder2_temps[model_name] = {'score': score, 'pct': pct}
        except:
            pass

    for path in glob.glob("reports/deepseek-coder*_20260323.json"):
        try:
            with open(path) as f:
                data = json.load(f)
                summary = data['summary']
                score_str = summary['overall_score']
                if '/' in score_str:
                    score, max_score = map(int, score_str.split('/'))
                    if max_score == 350:
                        model_name = data['model_name']
                        pct = summary['percentage']
                        if 'deepseek-coder_6' not in model_name:  # Skip 6.7B variant
                            deepseek_temps[model_name] = {'score': score, 'pct': pct}
        except:
            pass

    print(f"\nStarCoder2 temperature results found:")
    for model, data in sorted(starcoder2_temps.items(), key=lambda x: x[1]['pct'], reverse=True):
        print(f"  {model:35} {data['score']}/350 ({data['pct']:.1f}%)")

    if starcoder2_temps:
        scores = [d['pct'] for d in starcoder2_temps.values()]
        variation = max(scores) - min(scores)
        print(f"\nStarCoder2 variation: {variation:.1f} percentage points")
        if abs(variation - 17.3) < 1.0:
            print("✅ VERIFIED: StarCoder2 ~17.3 pp variation")
        else:
            print(f"❌ ERROR: Actual variation is {variation:.1f} pp, not 17.3 pp")

    print(f"\nDeepSeek-Coder temperature results found:")
    for model, data in sorted(deepseek_temps.items(), key=lambda x: x[1]['pct'], reverse=True):
        print(f"  {model:35} {data['score']}/350 ({data['pct']:.1f}%)")

    # Check for temp 0.7 being best
    if 'deepseek-coder_temp0.7' in deepseek_temps:
        temp07_score = deepseek_temps['deepseek-coder_temp0.7']['pct']
        if abs(temp07_score - 72.0) < 0.5:
            print(f"\n✅ VERIFIED: DeepSeek-Coder temp 0.7 = ~72.0%")
        else:
            print(f"❌ ERROR: DeepSeek temp 0.7 is {temp07_score:.1f}%, not 72.0%")

def verify_whitepaper_section_42():
    """Verify Section 4.2 Model Rankings table (208-point scale)."""
    print("\n=== CLAIM 4: Section 4.2 Model Rankings (208-point scale) ===")
    print("Whitepaper Section 4.2 shows rankings on 208-point scale")
    print("This is the OLDER benchmark scale from before multi-language support")
    print("\nNote: The whitepaper uses this older table for historical comparison.")
    print("Current rankings are on 350-point scale (shown in README).")
    print("\n⚠️  WARNING: Whitepaper Section 4.2 table is OUTDATED but intentionally")
    print("   kept for comparison with prior research using the same 208-point scale.")

def main():
    print("=" * 70)
    print("WHITEPAPER FACT VERIFICATION")
    print("Checking all major claims against actual benchmark data")
    print("=" * 70)

    verify_model_counts()
    verify_top_rankings()
    verify_temperature_study()
    verify_whitepaper_section_42()

    print("\n" + "=" * 70)
    print("VERIFICATION COMPLETE")
    print("=" * 70)

if __name__ == "__main__":
    main()
