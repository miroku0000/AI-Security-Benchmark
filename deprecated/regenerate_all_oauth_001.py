#!/usr/bin/env python3
"""Regenerate oauth_001.js for ALL models (71 models missing it)."""

import subprocess
import yaml
from pathlib import Path

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

print("Found oauth_001 prompt:")
print(f"  Prompt: {oauth_001['prompt'][:100]}...")
print()

# Create temp prompts file with just oauth_001
temp_prompts = {'prompts': [oauth_001]}
with open('/tmp/oauth_001_only.yaml', 'w') as f:
    yaml.dump(temp_prompts, f)

# Load list of models needing oauth_001
with open('/tmp/models_needing_oauth.txt', 'r') as f:
    model_dirs = [line.strip() for line in f if line.strip()]

print(f"Found {len(model_dirs)} models needing oauth_001 regeneration")
print()

# Map directory names to (model_name, provider, temperature)
# Format: directory -> (model, temp)
model_mapping = {}

for dir_name in model_dirs:
    # Parse directory name to extract model and temperature
    if '_temp' in dir_name:
        parts = dir_name.rsplit('_temp', 1)
        model_base = parts[0]
        temp = float(parts[1])
    else:
        model_base = dir_name
        temp = 0.0  # Default temperature

    # Remove any remaining suffixes
    if model_base.endswith('_6.7b-instruct'):
        model_base = model_base.replace('_6.7b-instruct', '')
    if model_base.endswith('_14b'):
        model_base = model_base.replace('_14b', '')

    model_mapping[dir_name] = (model_base, temp)

print("Model mapping created:")
print(f"  Total models: {len(model_mapping)}")
print()

# Group by model base
from collections import defaultdict
by_base = defaultdict(list)
for dir_name, (base, temp) in model_mapping.items():
    by_base[base].append((dir_name, temp))

print(f"Models grouped by base: {len(by_base)} unique models")
for base in sorted(by_base.keys())[:10]:
    temps = [t for _, t in by_base[base]]
    print(f"  {base}: {len(temps)} variants (temps: {sorted(set(temps))})")
print()

# Now regenerate for each model
successful = []
failed = []

total = len(model_dirs)
for idx, dir_name in enumerate(model_dirs, 1):
    model_base, temp = model_mapping[dir_name]
    output_dir = f"output/{dir_name}"

    print(f"{'='*70}")
    print(f"[{idx}/{total}] {dir_name}")
    print(f"  Model: {model_base}, Temp: {temp}, Output: {output_dir}")
    print(f"{'='*70}")

    cmd = [
        'python3', 'code_generator.py',
        '--model', model_base,
        '--temperature', str(temp),
        '--prompts', '/tmp/oauth_001_only.yaml',
        '--output', output_dir,
        '--force-regenerate',
        '--retries', '2'
    ]

    try:
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout per model
        )
        print(f"✓ SUCCESS: {dir_name}")
        successful.append(dir_name)
    except subprocess.TimeoutExpired:
        print(f"✗ TIMEOUT: {dir_name} (exceeded 5 minutes)")
        failed.append((dir_name, "timeout"))
    except subprocess.CalledProcessError as e:
        print(f"✗ FAILED: {dir_name} (exit code {e.returncode})")
        if e.stderr:
            print(f"  Error: {e.stderr[:200]}")
        failed.append((dir_name, f"exit_{e.returncode}"))
    except Exception as e:
        print(f"✗ ERROR: {dir_name} - {str(e)}")
        failed.append((dir_name, str(e)))

    print()

print("=" * 70)
print("REGENERATION COMPLETE")
print("=" * 70)
print(f"Total models: {total}")
print(f"✓ Successful: {len(successful)}")
print(f"✗ Failed: {len(failed)}")
print()

if failed:
    print("Failed models:")
    for model, reason in failed:
        print(f"  - {model}: {reason}")
    print()

# Save results
with open('/tmp/oauth_regen_results.txt', 'w') as f:
    f.write(f"OAuth 001 Regeneration Results\n")
    f.write(f"=" * 70 + "\n")
    f.write(f"Total: {total}\n")
    f.write(f"Successful: {len(successful)}\n")
    f.write(f"Failed: {len(failed)}\n\n")

    f.write("Successful models:\n")
    for m in successful:
        f.write(f"  ✓ {m}\n")
    f.write("\n")

    if failed:
        f.write("Failed models:\n")
        for m, r in failed:
            f.write(f"  ✗ {m}: {r}\n")

print("Results saved to: /tmp/oauth_regen_results.txt")
print("=" * 70)
