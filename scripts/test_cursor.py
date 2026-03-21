#!/usr/bin/env python3
"""
Test Cursor AI using cursor-agent headless mode.
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

def extract_code_from_cursor_output(output: str, language: str) -> str:
    """
    Extract code from Cursor's output.
    Cursor typically wraps code in markdown code blocks.
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

    # If no code blocks found, try to extract code after certain markers
    # Look for common code patterns
    lines = output.split('\n')
    code_lines = []
    in_code = False

    for line in lines:
        # Start collecting when we see function definitions, imports, etc.
        if any(keyword in line for keyword in ['def ', 'function ', 'import ', 'const ', 'let ', 'var ']):
            in_code = True

        if in_code:
            code_lines.append(line)

    if code_lines:
        return '\n'.join(code_lines).strip()

    # Last resort: return everything (might include explanations)
    return output.strip()

def run_cursor_agent(prompt: str, timeout: int = 60) -> tuple[str, bool]:
    """
    Run Cursor agent with a prompt and return the output.

    Returns:
        (output, success): The output text and whether it succeeded
    """
    try:
        result = subprocess.run(
            [
                'agent',
                '--print',  # Non-interactive mode
                '--output-format', 'text',  # Text output
                '--trust',  # Skip workspace prompts
                '--model', 'auto',  # Use Auto model (works on free plan)
                prompt
            ],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd='.'  # Use current directory as workspace
        )

        if result.returncode == 0:
            return result.stdout.strip(), True
        else:
            print(f"    ⚠️  agent returned non-zero exit code: {result.returncode}")
            print(f"    stderr: {result.stderr[:200]}")
            return result.stdout.strip() if result.stdout else result.stderr.strip(), False

    except subprocess.TimeoutExpired:
        print(f"    ⚠️  Timeout after {timeout}s")
        return "", False
    except FileNotFoundError:
        print("    ❌ agent command not found. Please install Cursor Agent:")
        print("    curl https://cursor.com/install -fsSL | bash")
        return "", False
    except Exception as e:
        print(f"    ❌ Error running agent: {e}")
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
        'c': 'c',
        'cpp': 'cpp',
        'csharp': 'cs',
        'ruby': 'rb',
        'php': 'php',
    }
    return extensions.get(language, 'txt')

def test_cursor_benchmark(prompts_file: Path, output_dir: Path, timeout: int = 60, limit: int = None):
    """
    Run Cursor on all prompts in the benchmark.
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
    print(f"CURSOR BENCHMARK TEST")
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
        'model_name': 'cursor',
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

        # Run cursor-agent
        output, success = run_cursor_agent(prompt_text, timeout)

        if success and output:
            # Extract code from output
            code = extract_code_from_cursor_output(output, language)

            if code:
                # Save to file
                file_ext = get_file_extension(language)
                output_file = output_dir / f"{prompt_id}.{file_ext}"

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
                'error': 'cursor-agent failed'
            })

        # Small delay to avoid overwhelming the system
        time.sleep(0.5)

    elapsed = time.time() - start_time

    # Save results summary
    results_file = output_dir / 'cursor_generation_results.json'
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
    print(f"1. Run security tests: python3 runner.py --code-dir {output_dir}")
    print(f"2. View results: cat reports/cursor_208point_*.json")
    print("=" * 80)

def main():
    parser = argparse.ArgumentParser(
        description='Test Cursor AI on security benchmark prompts'
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
        default=Path('output/cursor'),
        help='Output directory (default: output/cursor)'
    )
    parser.add_argument(
        '--timeout',
        type=int,
        default=60,
        help='Timeout per prompt in seconds (default: 60)'
    )
    parser.add_argument(
        '--limit',
        type=int,
        help='Limit number of prompts to test (for testing)'
    )
    parser.add_argument(
        '--cursor-path',
        type=str,
        help='Path to cursor-agent binary if not in PATH'
    )

    args = parser.parse_args()

    # Check if cursor-agent exists
    if args.cursor_path:
        # User provided custom path
        if not Path(args.cursor_path).exists():
            print(f"Error: cursor-agent not found at {args.cursor_path}")
            return
        print(f"Using cursor-agent at: {args.cursor_path}")
    else:
        # Check common locations
        common_paths = [
            '/Applications/Cursor.app/Contents/MacOS/cursor-agent',
            '/usr/local/bin/cursor-agent',
            '/opt/homebrew/bin/cursor-agent',
        ]

        found = False
        for path in common_paths:
            if Path(path).exists():
                print(f"Found cursor-agent at: {path}")
                found = True
                break

        if not found:
            print("Warning: cursor-agent not found in common locations.")
            print("If cursor-agent is not in your PATH, use --cursor-path to specify location.")
            print()

    test_cursor_benchmark(
        args.prompts,
        args.output_dir,
        args.timeout,
        args.limit
    )

if __name__ == '__main__':
    main()
