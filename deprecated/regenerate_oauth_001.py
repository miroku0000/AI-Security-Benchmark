#!/usr/bin/env python3
"""Regenerate oauth_001.js for primary models with fixed prompt."""

import subprocess
import yaml

# Load prompts
with open('prompts/prompts.yaml', 'r') as f:
    data = yaml.safe_load(f)
    prompts = data.get('prompts', [])

# Find oauth_001
oauth_001 = None
for p in prompts:
    if p.get('id') == 'oauth_001':
        oauth_001 = p
        break

if not oauth_001:
    print("ERROR: oauth_001 not found in prompts.yaml")
    exit(1)

print("Found oauth_001:")
print(f"  Prompt: {oauth_001['prompt'][:100]}...")
print(f"  Language: {oauth_001['language']}")
print(f"  Category: {oauth_001.get('category', 'N/A')}")
print()

# Create temp prompts file with just oauth_001
temp_prompts = {'prompts': [oauth_001]}
with open('/tmp/oauth_001_only.yaml', 'w') as f:
    yaml.dump(temp_prompts, f)

# Models to regenerate
models = [
    ('claude-sonnet-4-5', 'output/claude-sonnet-4-5', 0.0),
    ('claude-opus-4-6', 'output/claude-opus-4-6', 0.0),
    ('gpt-4o', 'output/gpt-4o', 0.0),
    ('gpt-5.4', 'output/gpt-5.4', 0.0),
    ('deepseek-coder', 'output/deepseek-coder', 0.0),
    ('qwen2.5-coder', 'output/qwen2.5-coder', 0.0),
    ('cursor', 'output/cursor', 0.0),
]

print(f"Regenerating oauth_001.js for {len(models)} models...")
print()

for model_name, output_dir, temp in models:
    print(f"{'='*70}")
    print(f"Model: {model_name}")
    print(f"Output: {output_dir}")
    print(f"{'='*70}")

    cmd = [
        'python3', 'code_generator.py',
        '--model', model_name,
        '--temperature', str(temp),
        '--prompts', '/tmp/oauth_001_only.yaml',
        '--output', output_dir,
        '--force-regenerate',
        '--retries', '2'
    ]

    try:
        result = subprocess.run(cmd, check=True, capture_output=False)
        print(f"✓ {model_name} completed")
    except subprocess.CalledProcessError as e:
        print(f"✗ {model_name} FAILED (exit code {e.returncode})")
    except Exception as e:
        print(f"✗ {model_name} ERROR: {e}")

    print()

print("="*70)
print("Regeneration complete!")
print("="*70)
