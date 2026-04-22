#!/usr/bin/env python3
"""Identify which model directories need oauth_001 regeneration."""

import os
from pathlib import Path

output_dir = Path("output")

# Get all model directories
model_dirs = sorted([d.name for d in output_dir.iterdir() if d.is_dir()])

print(f"Total model directories: {len(model_dirs)}")
print()

# Find models with full test suites (>= 700 files)
complete_models = []
for model in model_dirs:
    model_path = output_dir / model
    files = list(model_path.glob("*"))
    file_count = len(files)

    if file_count >= 700:
        has_oauth = (model_path / "oauth_001.js").exists() or (model_path / "oauth_001.txt").exists()
        complete_models.append((model, file_count, has_oauth))

print(f"Models with full test suites (>= 700 files): {len(complete_models)}")
print()

# Separate into has/needs oauth_001
has_oauth = [m for m in complete_models if m[2]]
needs_oauth = [m for m in complete_models if not m[2]]

print(f"✓ Has oauth_001: {len(has_oauth)}")
for model, count, _ in has_oauth:
    print(f"  - {model} ({count} files)")

print()
print(f"✗ Missing oauth_001: {len(needs_oauth)}")
for model, count, _ in needs_oauth:
    print(f"  - {model} ({count} files)")

print()
print("=" * 70)
print(f"Summary: {len(needs_oauth)} models need oauth_001 regeneration")
print("=" * 70)

# Save list for regeneration script
with open("/tmp/models_needing_oauth.txt", "w") as f:
    for model, _, _ in needs_oauth:
        f.write(f"{model}\n")

print(f"\nModel list saved to: /tmp/models_needing_oauth.txt")
