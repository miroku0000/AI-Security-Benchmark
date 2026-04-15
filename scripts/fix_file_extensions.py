#!/usr/bin/env python3
"""Fix file extensions across all output directories to match prompts.yaml definitions."""

import yaml
from pathlib import Path
import shutil

def main():
    # Load expected filenames from prompts.yaml
    with open('prompts/prompts.yaml') as f:
        data = yaml.safe_load(f)

    # Language extensions
    lang_ext = {
        'python': 'py', 'javascript': 'js', 'java': 'java', 'cpp': 'cpp',
        'go': 'go', 'rust': 'rs', 'csharp': 'cs', 'php': 'php',
        'typescript': 'ts', 'swift': 'swift', 'kotlin': 'kt', 'scala': 'scala',
        'dart': 'dart', 'ruby': 'rb', 'perl': 'pl', 'lua': 'lua', 'c': 'c',
        'solidity': 'sol', 'bash': 'sh', 'elixir': 'ex', 'groovy': 'groovy',
        'yaml': 'yaml', 'terraform': 'tf', 'dockerfile': 'Dockerfile',
        'xml': 'xml', 'json': 'json', 'conf': 'conf'
    }

    # Build expected filename set and prompt ID lookup
    expected_files = {}
    prompt_ids = {}
    for prompt in data['prompts']:
        id = prompt['id']
        lang = prompt.get('language', '')
        ext = lang_ext.get(lang, lang)
        filename = f'{id}.{ext}'
        expected_files[filename] = (id, ext)
        prompt_ids[id] = (lang, ext)

    print('=' * 80)
    print('FILE EXTENSION CLEANUP')
    print('=' * 80)
    print(f'Expected files: {len(expected_files)}')
    print()

    total_removed = 0
    total_renamed = 0
    dirs_processed = 0

    output_dir = Path('output')

    for model_dir in sorted(output_dir.glob('*')):
        if not model_dir.is_dir():
            continue

        # Skip test directories
        if model_dir.name.startswith('test_'):
            continue

        actual_files = {f.name: f for f in model_dir.glob('*') if f.is_file()}

        # Skip if already correct
        extra = set(actual_files.keys()) - set(expected_files.keys())
        if not extra:
            continue

        dirs_processed += 1
        print(f'{model_dir.name}:')

        removed_count = 0
        renamed_count = 0

        for filename, file_path in actual_files.items():
            # Check if this is an expected file
            if filename in expected_files:
                continue

            # Check if this is a metadata file
            if filename.endswith('_generation_results.json') or filename.endswith('_results.json'):
                print(f'  Removing metadata: {filename}')
                file_path.unlink()
                removed_count += 1
                continue

            # Extract prompt ID from filename (e.g., "supply_032.conf" -> "supply_032")
            stem = file_path.stem

            # Check if this prompt ID exists and has wrong extension
            if stem in prompt_ids:
                expected_lang, expected_ext = prompt_ids[stem]
                expected_filename = f'{stem}.{expected_ext}'

                # Rename to correct extension
                new_path = model_dir / expected_filename
                if not new_path.exists():
                    print(f'  Renaming: {filename} -> {expected_filename}')
                    file_path.rename(new_path)
                    renamed_count += 1
                else:
                    print(f'  Removing duplicate: {filename} (expected file exists)')
                    file_path.unlink()
                    removed_count += 1
            else:
                # This is from an old/removed prompt
                print(f'  Removing obsolete: {filename}')
                file_path.unlink()
                removed_count += 1

        if removed_count > 0 or renamed_count > 0:
            print(f'  Summary: {renamed_count} renamed, {removed_count} removed')
            total_renamed += renamed_count
            total_removed += removed_count

        print()

    print('=' * 80)
    print('CLEANUP SUMMARY')
    print('=' * 80)
    print(f'Directories processed: {dirs_processed}')
    print(f'Files renamed: {total_renamed}')
    print(f'Files removed: {total_removed}')

    # Verify all directories now have correct file counts
    print()
    print('Verifying file counts...')
    issues = []
    for model_dir in sorted(output_dir.glob('*')):
        if not model_dir.is_dir() or model_dir.name.startswith('test_'):
            continue

        file_count = len([f for f in model_dir.glob('*') if f.is_file()])
        if file_count != 730:
            issues.append((model_dir.name, file_count))

    if issues:
        print(f'\nDirectories still with incorrect file counts ({len(issues)}):')
        for name, count in issues:
            print(f'  {name}: {count} files')
    else:
        print('✅ All directories have exactly 730 files!')

if __name__ == '__main__':
    main()
