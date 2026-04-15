#!/usr/bin/env python3
"""
Identify models with complete or near-complete file generation (>=700 files).
"""
import os
from pathlib import Path

def count_model_files():
    """Count generated files for each model."""
    output_dir = Path("output")
    models = {}

    for model_dir in output_dir.iterdir():
        if model_dir.is_dir():
            file_count = len(list(model_dir.glob("*")))
            models[model_dir.name] = file_count

    return models

if __name__ == "__main__":
    models = count_model_files()

    # Filter models with >= 700 files and sort by count
    complete_models = {k: v for k, v in models.items() if v >= 700}
    sorted_models = sorted(complete_models.items(), key=lambda x: x[1], reverse=True)

    print("=" * 80)
    print("MODELS WITH COMPLETE/NEAR-COMPLETE GENERATION (>=700 files)")
    print("=" * 80)
    print(f"Total models found: {len(sorted_models)}")
    print(f"Expected files per model: 760")
    print()

    for model, count in sorted_models:
        completion = (count / 760) * 100
        status = "COMPLETE" if count >= 760 else f"{760 - count} missing"
        print(f"{model:40s} {count:4d} files  ({completion:5.1f}%)  {status}")

    print()
    print("Models with 760 files:")
    complete_760 = [m for m, c in sorted_models if c >= 760]
    for model in complete_760:
        print(f"  - {model}")
