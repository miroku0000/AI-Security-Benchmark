#!/usr/bin/env python3
"""
Test GitHub Copilot CLI using the copilot command.
Generates code for all prompts in the benchmark.
"""

import yaml
import subprocess
import argparse
import json
from pathlib import Path
from datetime import datetime
import time
import re

def extract_code_from_copilot_output(output: str, language: str) -> str:
    """
    Extract code from Copilot's output.
    Copilot may include explanations before code or wrap code in markdown.
    """
    # Try to find code blocks with language specifier
    pattern = rf'```{language}\n(.*?)\n```'
    matches = re.findall(pattern, output, re.DOTALL | re.IGNORECASE)

    if matches:
        return matches[0].strip()

    # Try generic code blocks
    pattern = r'```\n(.*?)\n```'
    matches = re.findall(pattern, output, re.DOTALL)

    if matches:
        return matches[0].strip()

    # If no code blocks found, look for code start markers
    # Copilot often includes explanation text before the actual code starts
    lines = output.split('\n')
    code_lines = []
    in_code = False

    # Common code start patterns
    code_start_patterns = [
        r'^#!/',  # Shebang
        r'^import\s+',
        r'^from\s+\w+\s+import',
        r'^def\s+\w+',
        r'^class\s+\w+',
        r'^function\s+\w+',
        r'^const\s+\w+',
        r'^let\s+\w+',
        r'^var\s+\w+',
        r'^package\s+',
        r'^use\s+',
        r'^#include\s+',
        r'^public\s+class',
        r'^fn\s+\w+',  # Rust
        r'^func\s+\w+',  # Go
    ]

    for i, line in enumerate(lines):
        # Skip empty lines at the start
        if not in_code and not line.strip():
            continue

        # Check if this line starts code
        if not in_code:
            for pattern in code_start_patterns:
                if re.match(pattern, line):
                    in_code = True
                    break

        if in_code:
            code_lines.append(line)

    if code_lines:
        return '\n'.join(code_lines).strip()

    # Last resort: return everything (might include explanations)
    return output.strip()

def run_copilot(prompt: str, timeout: int = 120) -> tuple[str, bool]:
    """
    Run GitHub Copilot CLI with a prompt and return the output.

    Returns:
        (output, success): The output text and whether it succeeded
    """
    try:
        result = subprocess.run(
            [
                'copilot',
                '-p', prompt,
                '-s'  # Suppress interactive prompts
            ],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd='.'
        )

        if result.returncode == 0:
            return result.stdout.strip(), True
        else:
            print(f"    ⚠️  copilot returned non-zero exit code: {result.returncode}")
            print(f"    stderr: {result.stderr[:200]}")
            return result.stdout.strip() if result.stdout else result.stderr.strip(), False

    except subprocess.TimeoutExpired:
        print(f"    ⚠️  Timeout after {timeout}s")
        return "", False
    except FileNotFoundError:
        print("    ❌ copilot command not found. Please install GitHub Copilot CLI:")
        print("    Visit: https://docs.github.com/en/copilot/github-copilot-in-the-cli")
        return "", False
    except Exception as e:
        print(f"    ❌ Error running copilot: {e}")
        return "", False

def get_file_extension(language: str) -> str:
    """Get file extension for language."""
    extensions = {
        'python': 'py',
        'javascript': 'js',
        'typescript': 'ts',
        'java': 'java',
        'go': 'go',
        'rust': 'rs',
        'cpp': 'cpp',
        'c++': 'cpp',
        'c': 'c',
        'csharp': 'cs',
        'c#': 'cs',
        'scala': 'scala',
        'php': 'php',
        'ruby': 'rb',
        'bash': 'sh',
        'shell': 'sh',
        'perl': 'pl',
        'lua': 'lua',
        'elixir': 'ex',
        'solidity': 'sol',
        'swift': 'swift',
        'kotlin': 'kt',
        'dart': 'dart',
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
        'conf': 'conf',
        'config': 'conf',
        'groovy': 'groovy',
    }
    return extensions.get(language.lower(), 'txt')

def test_copilot_benchmark(prompts_file: Path, output_dir: Path, timeout: int = 120, limit: int = None):
    """
    Run GitHub Copilot CLI on all prompts in the benchmark.
    """
    # Load prompts
    with open(prompts_file) as f:
        data = yaml.safe_load(f)

    # Handle both formats: direct list or {'prompts': [list]}
    if isinstance(data, dict) and 'prompts' in data:
        prompts = data['prompts']
    elif isinstance(data, list):
        prompts = data
    else:
        print(f"Unexpected YAML format in {prompts_file}")
        return

    if not prompts:
        print(f"No prompts found in {prompts_file}")
        return

    # Apply limit if specified
    if limit and limit > 0:
        prompts = prompts[:limit]

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print(f"GITHUB COPILOT CLI BENCHMARK TEST")
    print("=" * 80)
    print(f"Prompts file: {prompts_file}")
    print(f"Output dir:   {output_dir}")
    print(f"Total prompts: {len(prompts)}")
    print(f"Timeout:      {timeout}s per prompt")
    print("=" * 80)
    print()

    # Results tracking
    results = {
        'benchmark_date': datetime.now().isoformat(),
        'model_name': 'github-copilot',
        'total_prompts': len(prompts),
        'completed': 0,
        'failed': 0,
        'prompts': []
    }

    start_time = time.time()

    for i, prompt_data in enumerate(prompts, 1):
        prompt_id = prompt_data.get('id', f'prompt_{i}')
        prompt_text = prompt_data.get('prompt', '')
        category = prompt_data.get('category', 'unknown')
        language = prompt_data.get('language', 'python')

        print(f"[{i}/{len(prompts)}] {prompt_id} ({category}, {language})...")

        # Check if file already exists
        file_ext = get_file_extension(language)
        output_file = output_dir / f"{prompt_id}.{file_ext}"

        # Check for exact match first
        if output_file.exists():
            print(f"  ⏭️  Already exists (skipped)")
            results['completed'] += 1
            results['prompts'].append({
                'id': prompt_id,
                'category': category,
                'language': language,
                'output_file': str(output_file),
                'success': True,
                'skipped': True
            })
            continue

        # Check for any file with the same base name but different extension
        found_alternative = False
        for existing in output_dir.glob(f"{prompt_id}.*"):
            if existing.is_file() and existing != output_file:
                print(f"  ⏭️  Already exists as {existing.name} (skipped)")
                results['completed'] += 1
                results['prompts'].append({
                    'id': prompt_id,
                    'category': category,
                    'language': language,
                    'output_file': str(existing),
                    'success': True,
                    'skipped': True
                })
                found_alternative = True
                break

        if found_alternative:
            continue

        # Enhance prompt to request code only
        enhanced_prompt = f"{prompt_text}\n\nProvide only the complete, runnable code. Do not include explanations or markdown formatting."

        # Run copilot
        output, success = run_copilot(enhanced_prompt, timeout)

        if success and output:
            # Extract code from output
            code = extract_code_from_copilot_output(output, language)

            if code:
                # Save to file
                with open(output_file, 'w') as f:
                    f.write(code)

                print(f"  ✅ Saved to {output_file}")
                results['completed'] += 1

                results['prompts'].append({
                    'id': prompt_id,
                    'category': category,
                    'language': language,
                    'output_file': str(output_file),
                    'success': True,
                    'code_length': len(code)
                })
            else:
                print(f"  ⚠️  No code extracted from output")
                results['failed'] += 1
                results['prompts'].append({
                    'id': prompt_id,
                    'category': category,
                    'language': language,
                    'success': False,
                    'error': 'No code extracted'
                })
        else:
            print(f"  ❌ Failed")
            results['failed'] += 1
            results['prompts'].append({
                'id': prompt_id,
                'category': category,
                'language': language,
                'success': False,
                'error': 'copilot command failed'
            })

        # Small delay to avoid rate limiting
        time.sleep(1)

    elapsed = time.time() - start_time

    # Save results summary
    results_file = output_dir / 'github_copilot_generation_results.json'
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)

    # Print summary
    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total prompts:  {results['total_prompts']}")
    print(f"Completed:      {results['completed']}")
    print(f"Failed:         {results['failed']}")
    print(f"Success rate:   {results['completed']/results['total_prompts']*100:.1f}%")
    print(f"Time elapsed:   {elapsed:.1f}s ({elapsed/len(prompts):.1f}s per prompt)")
    print(f"Results saved:  {results_file}")
    print("=" * 80)
    print()
    print("NEXT STEPS:")
    print(f"1. Run security tests: python3 runner.py --code-dir {output_dir} --model github-copilot")
    print(f"2. View results: cat reports/github-copilot.json")
    print("=" * 80)

def main():
    parser = argparse.ArgumentParser(
        description='Test GitHub Copilot CLI on security benchmark prompts'
    )
    parser.add_argument(
        '--prompts',
        type=Path,
        default=Path('prompts/prompts.yaml'),
        help='Prompts file (default: prompts/prompts.yaml)'
    )
    parser.add_argument(
        '--output-dir',
        type=Path,
        default=Path('output/github-copilot'),
        help='Output directory (default: output/github-copilot)'
    )
    parser.add_argument(
        '--timeout',
        type=int,
        default=120,
        help='Timeout per prompt in seconds (default: 120)'
    )
    parser.add_argument(
        '--limit',
        type=int,
        help='Limit number of prompts to test (for testing)'
    )

    args = parser.parse_args()

    # Check if copilot command exists
    try:
        subprocess.run(['copilot', '--version'], capture_output=True, check=True)
        print("✅ GitHub Copilot CLI found")
        print()
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ GitHub Copilot CLI not found")
        print("Please install it from: https://docs.github.com/en/copilot/github-copilot-in-the-cli")
        print()
        return

    test_copilot_benchmark(
        args.prompts,
        args.output_dir,
        args.timeout,
        args.limit
    )

if __name__ == '__main__':
    main()
