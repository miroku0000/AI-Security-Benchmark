#!/usr/bin/env python3
"""
Extract baseline model rankings from all reports.
Filters out temperature variants and security-level tests.
"""

import json
import glob
from typing import List, Dict

def is_baseline_config(model_name: str) -> bool:
    """Check if this is a baseline configuration (not temp or level variant)."""
    # Exclude temperature variants
    if '_temp' in model_name.lower():
        return False
    # Exclude security level variants
    if '_level' in model_name.lower():
        return False
    # Include everything else (base models and wrapper apps)
    return True

def extract_rankings() -> List[Dict]:
    """Extract all baseline rankings from reports."""
    rankings = []

    # Load all March 23, 2026 reports
    for path in sorted(glob.glob("reports/*_20260323.json")):
        try:
            with open(path) as f:
                data = json.load(f)

            model_name = data.get('model_name', 'Unknown')

            # Skip non-baseline configs
            if not is_baseline_config(model_name):
                continue

            summary = data.get('summary', {})
            score_str = summary.get('overall_score', '0/0')

            if '/' not in score_str:
                continue

            score, max_score = map(int, score_str.split('/'))
            percentage = summary.get('percentage', 0.0)

            rankings.append({
                'model': model_name,
                'score': score,
                'max_score': max_score,
                'percentage': percentage,
                'path': path
            })
        except Exception as e:
            print(f"Error processing {path}: {e}")

    return rankings

def categorize_model(model_name: str) -> tuple:
    """Return (provider, type) for a model."""
    name_lower = model_name.lower()

    # Wrapper applications
    if 'codex-app' in name_lower:
        if 'security-skill' in name_lower:
            return ('OpenAI', 'Wrapper (GPT-5.4)')
        else:
            return ('OpenAI', 'Wrapper (GPT-5.4)')
    if 'claude-code' in name_lower:
        return ('Anthropic', 'Wrapper (Sonnet 4.5)')
    if 'cursor' in name_lower:
        return ('Unknown', 'Wrapper')

    # API models
    if any(x in name_lower for x in ['gpt-', 'o1', 'o3']):
        return ('OpenAI', 'API')
    if 'claude' in name_lower:
        return ('Anthropic', 'API')
    if 'gemini' in name_lower:
        return ('Google', 'API')

    # Ollama local models
    return ('Ollama', 'Local')

def main():
    rankings = extract_rankings()

    # Sort by score descending
    rankings.sort(key=lambda x: (x['score'], x['percentage']), reverse=True)

    print("=" * 100)
    print("BASELINE MODEL RANKINGS (Default Temperatures, March 23 2026)")
    print("=" * 100)
    print()
    print(f"Total configurations found: {len(rankings)}")
    print()

    # Print rankings table
    print(f"{'Rank':<6} {'Model/Application':<45} {'Score':<12} {'%':<8} {'Provider':<12} {'Type':<20}")
    print("-" * 100)

    for i, r in enumerate(rankings, 1):
        provider, model_type = categorize_model(r['model'])
        print(f"{i:<6} {r['model']:<45} {r['score']}/{r['max_score']:<7} {r['percentage']:>6.1f}%  {provider:<12} {model_type:<20}")

    print()
    print("=" * 100)

    # Group by scale
    by_scale = {}
    for r in rankings:
        scale = r['max_score']
        if scale not in by_scale:
            by_scale[scale] = []
        by_scale[scale].append(r)

    print()
    print("BREAKDOWN BY SCALE:")
    for scale in sorted(by_scale.keys(), reverse=True):
        print(f"\n{scale}-point scale: {len(by_scale[scale])} configurations")

if __name__ == "__main__":
    main()
