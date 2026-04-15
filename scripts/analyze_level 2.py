#!/usr/bin/env python3
"""
Analyze security for a specific prompt level directory.
Handles _levelN file naming by creating temporary links.
"""
import os
import sys
import argparse
import tempfile
import shutil
from pathlib import Path

def analyze_level(level_dir, level_num, model_name):
    """Analyze a level directory by creating temp directory with proper names."""

    level_path = Path(level_dir)
    if not level_path.exists():
        print(f"ERROR: Directory not found: {level_dir}")
        return 1

    # Create temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        print(f"Creating temporary analysis directory: {temp_dir}")

        # Copy files, removing _levelN suffix
        files_copied = 0
        for file in level_path.iterdir():
            if file.is_file():
                # Remove _levelN from filename
                new_name = file.name.replace(f"_level{level_num}", "")
                dest = temp_path / new_name
                shutil.copy(file, dest)
                files_copied += 1

        print(f"Copied {files_copied} files to temporary directory")

        # Always use baseline prompts file for prompt IDs
        # The level-specific prompts have different text but same IDs with _levelN suffix
        # We need the baseline IDs that match our renamed files
        prompts_file = "prompts/prompts.yaml"

        if not os.path.exists(prompts_file):
            print(f"ERROR: Prompts file not found: {prompts_file}")
            return 1

        # Run analysis
        output_file = f"reports/{model_name}_level{level_num}_208point_{Path.cwd().name.split('_')[-1]}.json"

        cmd = f"python3 runner.py --code-dir {temp_dir} --model {model_name}_level{level_num} --prompts {prompts_file} --output {output_file}"
        print(f"\nRunning: {cmd}\n")

        result = os.system(cmd)

        if result == 0:
            print(f"\n✅ Analysis complete! Report saved to: {output_file}")
            print(f"HTML report: {output_file.replace('.json', '.html')}")
        else:
            print(f"\n❌ Analysis failed with exit code: {result}")

        return result

def main():
    parser = argparse.ArgumentParser(description='Analyze security for a specific prompt level')
    parser.add_argument('--level-dir', required=True, help='Directory containing level files (e.g., output/deepseek-coder_level1)')
    parser.add_argument('--level', type=int, required=True, help='Level number (0-5)')
    parser.add_argument('--model', required=True, help='Model name (e.g., deepseek-coder, gpt-4o-mini)')

    args = parser.parse_args()

    sys.exit(analyze_level(args.level_dir, args.level, args.model))

if __name__ == '__main__':
    main()
