#!/usr/bin/env python3
"""
Rename .txt files in Codex.app output to correct file extensions based on language.
"""

import yaml
from pathlib import Path
import argparse

def get_file_extension(language: str) -> str:
    """Get file extension for language - must match test_codex_app.py."""
    extensions = {
        'python': 'py',
        'javascript': 'js',
        'typescript': 'ts',
        'java': 'java',
        'go': 'go',
        'rust': 'rs',
        'cpp': 'cpp',
        'c++': 'cpp',
        'csharp': 'cs',
        'c#': 'cs',
        'scala': 'scala',
        'php': 'php',
        'ruby': 'rb',
        'bash': 'sh',
        'shell': 'sh',
        'perl': 'pl',
        'swift': 'swift',
        'kotlin': 'kt',
        'terraform': 'tf',
        'hcl': 'tf',
        'azure': 'json',
        'arm': 'json',
        'cloudformation': 'yaml',
        'cfn': 'yaml',
        'dockerfile': 'Dockerfile',
        'yaml': 'yaml',
        'yml': 'yaml',
        'json': 'json',
        'xml': 'xml',
        'sql': 'sql',
        'graphql': 'graphql',
        'proto': 'proto',
        'protobuf': 'proto',
        'dart': 'dart',
        'conf': 'conf',
        'config': 'conf',
        'groovy': 'groovy',
        'elixir': 'ex',
        'lua': 'lua',
        'solidity': 'sol',
        'c': 'c',
    }
    return extensions.get(language.lower(), 'txt')

def load_prompt_languages(prompts_file: Path) -> dict:
    """Load prompt ID to language mapping from prompts.yaml."""
    with open(prompts_file) as f:
        data = yaml.safe_load(f)

    if isinstance(data, dict) and 'prompts' in data:
        prompts = data['prompts']
    elif isinstance(data, list):
        prompts = data
    else:
        raise ValueError(f"Unexpected YAML format in {prompts_file}")

    # Build mapping: prompt_id -> language
    mapping = {}
    for prompt in prompts:
        prompt_id = prompt.get('id')
        language = prompt.get('language', 'python')
        if prompt_id:
            mapping[prompt_id] = language

    return mapping

def rename_txt_files(output_dir: Path, prompts_file: Path, dry_run: bool = False):
    """Rename .txt files to correct extensions based on prompt language."""

    # Load prompt languages
    print(f"Loading prompt languages from {prompts_file}...")
    language_map = load_prompt_languages(prompts_file)
    print(f"Loaded {len(language_map)} prompt language mappings")

    # Find all .txt files
    txt_files = list(output_dir.glob('*.txt'))
    print(f"\nFound {len(txt_files)} .txt files in {output_dir}")

    if not txt_files:
        print("No .txt files to rename!")
        return

    renamed_count = 0
    skipped_count = 0
    error_count = 0

    for txt_file in txt_files:
        # Extract prompt ID from filename (e.g., "terraform_015.txt" -> "terraform_015")
        prompt_id = txt_file.stem

        # Look up language
        language = language_map.get(prompt_id)

        if not language:
            print(f"  ⚠️  {txt_file.name}: No language found for prompt_id '{prompt_id}' - SKIPPED")
            skipped_count += 1
            continue

        # Get correct extension
        correct_ext = get_file_extension(language)

        if correct_ext == 'txt':
            print(f"  ⚠️  {txt_file.name}: Language '{language}' maps to .txt - SKIPPED")
            skipped_count += 1
            continue

        # Build new filename
        new_file = txt_file.parent / f"{prompt_id}.{correct_ext}"

        # Check if target already exists
        if new_file.exists():
            print(f"  ⚠️  {txt_file.name} -> {new_file.name}: Target exists - SKIPPED")
            skipped_count += 1
            continue

        # Rename
        if dry_run:
            print(f"  [DRY RUN] {txt_file.name} -> {new_file.name} (language: {language})")
            renamed_count += 1
        else:
            try:
                txt_file.rename(new_file)
                print(f"  ✅ {txt_file.name} -> {new_file.name} (language: {language})")
                renamed_count += 1
            except Exception as e:
                print(f"  ❌ {txt_file.name}: Error renaming - {e}")
                error_count += 1

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total .txt files:  {len(txt_files)}")
    print(f"Renamed:           {renamed_count}")
    print(f"Skipped:           {skipped_count}")
    print(f"Errors:            {error_count}")
    print("=" * 80)

    if dry_run:
        print("\n⚠️  This was a DRY RUN. Run without --dry-run to actually rename files.")

def main():
    parser = argparse.ArgumentParser(
        description='Rename .txt files to correct extensions based on prompt language'
    )
    parser.add_argument(
        '--output-dir',
        type=Path,
        required=True,
        help='Directory containing .txt files to rename (e.g., output/codex-app-security-skill)'
    )
    parser.add_argument(
        '--prompts',
        type=Path,
        default=Path('prompts/prompts.yaml'),
        help='Prompts file (default: prompts/prompts.yaml)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be renamed without actually renaming'
    )

    args = parser.parse_args()

    if not args.output_dir.exists():
        print(f"ERROR: Output directory does not exist: {args.output_dir}")
        return 1

    if not args.prompts.exists():
        print(f"ERROR: Prompts file does not exist: {args.prompts}")
        return 1

    rename_txt_files(args.output_dir, args.prompts, args.dry_run)
    return 0

if __name__ == '__main__':
    exit(main())
