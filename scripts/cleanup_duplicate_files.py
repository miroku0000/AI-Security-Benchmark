#!/usr/bin/env python3
"""Remove macOS Finder duplicate files (files with ' 2', ' 3', etc. in the name)."""

import re
from pathlib import Path

def cleanup_directory(dir_path):
    """Remove duplicate files from a directory."""
    if not dir_path.exists():
        return 0, 0
    
    all_files = [f for f in dir_path.glob('*') if f.is_file()]
    removed_count = 0
    kept_count = 0
    
    # Pattern to match: filename 2.ext, filename 3.ext, etc.
    duplicate_pattern = re.compile(r' \d+\.')
    
    for file_path in all_files:
        if duplicate_pattern.search(file_path.name):
            # This is a duplicate
            print(f'  Removing: {file_path.name}')
            file_path.unlink()
            removed_count += 1
        else:
            kept_count += 1
    
    return kept_count, removed_count

def main():
    output_dir = Path('output')
    
    print('=== Cleaning up duplicate files ===\n')
    
    total_kept = 0
    total_removed = 0
    dirs_cleaned = 0
    
    for model_dir in sorted(output_dir.glob('*')):
        if not model_dir.is_dir():
            continue
        
        kept, removed = cleanup_directory(model_dir)
        
        if removed > 0:
            print(f'{model_dir.name}: Kept {kept}, Removed {removed}')
            dirs_cleaned += 1
            total_kept += kept
            total_removed += removed
    
    print(f'\n=== Summary ===')
    print(f'Directories cleaned: {dirs_cleaned}')
    print(f'Files kept: {total_kept}')
    print(f'Files removed: {total_removed}')

if __name__ == '__main__':
    main()
