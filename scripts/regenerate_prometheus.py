#!/usr/bin/env python3
"""
Regenerate only prometheus-related prompts for all models
Uses observability_metrics_001 (fair baseline) instead of obs_prometheus_001 (adversarial)
"""
import subprocess
import sys
from pathlib import Path

# List of all baseline models (excluding temp/level variants)
BASELINE_MODELS = [
    'claude-code',
    'claude-opus-4-6',
    'claude-sonnet-4-5',
    'codegemma',
    'codellama',
    'codex-app-no-skill',
    'codex-app-security-skill',
    'codex',
    'cursor',
    'deepseek-coder_6.7b-instruct',
    'deepseek-coder',
    'gemini-2.5-flash',
    'gpt-3.5-turbo',
    'gpt-4',
    'gpt-4o-mini',
    'gpt-4o',
    'gpt-5.2',
    'gpt-5.4-mini',
    'gpt-5.4',
    'llama3.1',
    'mistral',
    'o1',
    'o3-mini',
    'o3',
    'qwen2.5-coder_14b',
    'qwen2.5-coder',
    'starcoder2'
]

# Prometheus prompt IDs to regenerate (using fair baseline IDs)
PROMETHEUS_PROMPTS = [
    'observability_metrics_001',  # Fair baseline
    # obs_prometheus_002 and 003 are different categories (cardinality, sensitive_metrics)
    # We'll skip those for now since they test different vulnerabilities
]

def regenerate_for_model(model_name):
    """Regenerate prometheus prompts for a single model"""
    print(f"\n{'='*80}")
    print(f"Regenerating prometheus prompts for: {model_name}")
    print(f"{'='*80}")

    for prompt_id in PROMETHEUS_PROMPTS:
        print(f"\n  Generating {prompt_id}...")

        # Run code_generator.py for this specific prompt
        cmd = [
            'python3', 'code_generator.py',
            '--model', model_name,
            '--prompts', 'prompts/prompts.yaml',
            '--prompt-id', prompt_id
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

            if result.returncode == 0:
                print(f"    ✅ Generated {prompt_id}")
            else:
                print(f"    ❌ Failed to generate {prompt_id}")
                print(f"    Error: {result.stderr[:200]}")
        except subprocess.TimeoutExpired:
            print(f"    ⏱️  Timeout generating {prompt_id}")
        except Exception as e:
            print(f"    ❌ Exception: {e}")

    print(f"\n✅ Completed {model_name}")

def main():
    print("="*80)
    print("PROMETHEUS PROMPTS REGENERATION")
    print("="*80)
    print(f"\nTarget models: {len(BASELINE_MODELS)}")
    print(f"Prompts to regenerate: {len(PROMETHEUS_PROMPTS)}")
    print(f"Total operations: {len(BASELINE_MODELS) * len(PROMETHEUS_PROMPTS)}")
    print("\nUsing FAIR BASELINE prompts (observability_metrics_*)")
    print("="*80)

    # Confirm before proceeding
    response = input("\nProceed with regeneration? (yes/no): ").strip().lower()
    if response != 'yes':
        print("Aborted.")
        sys.exit(0)

    success_count = 0
    fail_count = 0

    for model_name in BASELINE_MODELS:
        try:
            regenerate_for_model(model_name)
            success_count += 1
        except Exception as e:
            print(f"❌ Failed to process {model_name}: {e}")
            fail_count += 1

    print("\n" + "="*80)
    print("REGENERATION SUMMARY")
    print("="*80)
    print(f"✅ Successful: {success_count}")
    print(f"❌ Failed: {fail_count}")
    print("="*80)

if __name__ == '__main__':
    main()
