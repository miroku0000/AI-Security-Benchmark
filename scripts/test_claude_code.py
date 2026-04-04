#!/usr/bin/env python3
"""
Test Claude Code CLI on security benchmark.

Claude Code is Anthropic's official CLI for Claude, similar to how Codex.app
is OpenAI's desktop application. This tests whether Claude Code's wrapper
adds security value over the raw Claude API.
"""

import yaml
import subprocess
import argparse
import json
from pathlib import Path
from datetime import datetime
import time
import re
import shutil

CLAUDE_CLI = "claude"

def check_claude_installed():
    """Check if Claude Code CLI is installed and accessible."""
    claude_path = shutil.which(CLAUDE_CLI)
    if not claude_path:
        print(f"ERROR: Claude Code CLI not found in PATH")
        print("Please install Claude Code from Anthropic")
        return False

    try:
        result = subprocess.run(
            [CLAUDE_CLI, "--version"],
            capture_output=True,
            text=True,
            timeout=10
        )
        version = result.stdout.strip() or result.stderr.strip()
        print(f"✓ Found Claude Code CLI: {version}")
        return True
    except Exception as e:
        print(f"ERROR: Could not run Claude CLI: {e}")
        return False

def generate_code_with_claude(prompt: str, timeout: int = 120) -> tuple[str, bool, str]:
    """
    Generate code using Claude Code CLI.

    Returns:
        (code, success, failure_reason): The generated code, whether it succeeded, and reason for failure
    """
    try:
        # Enhanced prompt to get code only
        enhanced_prompt = f"""{prompt}

IMPORTANT: Output ONLY the complete, runnable code. No explanations, descriptions, markdown blocks, or commentary. Just the raw code file contents that can be directly saved and executed."""

        # Run claude command in print mode (non-interactive)
        # --print: Print response and exit
        # --dangerously-skip-permissions: Skip permission dialogs for automation
        result = subprocess.run(
            [CLAUDE_CLI, "--print", "--dangerously-skip-permissions", enhanced_prompt],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd="."
        )

        if result.returncode == 0:
            output = result.stdout.strip()

            # Claude may still include markdown or explanatory text
            # Try to extract just the code
            code = extract_code_from_output(output)

            if code:
                return code, True, None
            else:
                failure_reason = f"parse_error: No code extracted from {len(output)} chars output"
                print(f"    ⚠️  No code extracted (got {len(output)} chars)")
                return output, False, failure_reason
        else:
            error = result.stderr.strip()
            failure_reason = f"cli_error: {error[:100]}"
            print(f"    ⚠️  Claude returned error: {error}")
            return "", False, failure_reason

    except subprocess.TimeoutExpired:
        failure_reason = f"timeout: Exceeded {timeout}s limit"
        print(f"    ⚠️  Timeout after {timeout}s")
        return "", False, failure_reason
    except Exception as e:
        failure_reason = f"exception: {str(e)}"
        print(f"    ❌ Error: {e}")
        return "", False, failure_reason

def extract_code_from_output(output: str) -> str:
    """
    Extract code from Claude output.
    Claude may include explanatory text before/after code blocks.
    """
    # Try to find code blocks first
    code_block_pattern = r'```(?:\w+)?\n(.*?)\n```'
    matches = re.findall(code_block_pattern, output, re.DOTALL)
    if matches:
        # Take the largest code block
        return max(matches, key=len).strip()

    # If no code blocks, look for code patterns
    # Split by double newlines and take the largest chunk
    chunks = output.split('\n\n')
    if chunks:
        # Find chunk with most code-like patterns
        def code_score(text):
            score = 0
            score += text.count('def ') * 10
            score += text.count('function ') * 10
            score += text.count('import ') * 5
            score += text.count('const ') * 5
            score += text.count('class ') * 10
            score += text.count('{') * 2
            score += text.count('(') * 1
            return score

        chunks_scored = [(chunk, code_score(chunk)) for chunk in chunks]
        chunks_scored.sort(key=lambda x: x[1], reverse=True)

        if chunks_scored[0][1] > 10:  # Has some code patterns
            return chunks_scored[0][0].strip()

    # Last resort: return everything
    return output.strip()

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

def test_claude_code_benchmark(
    prompts_file: Path,
    output_dir: Path,
    timeout: int = 600,
    limit: int = None
):
    """
    Run Claude Code CLI on all prompts in the benchmark.
    """
    # Load prompts
    with open(prompts_file) as f:
        data = yaml.safe_load(f)

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

    # Apply limit
    if limit and limit > 0:
        prompts = prompts[:limit]

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print(f"CLAUDE CODE CLI BENCHMARK TEST")
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
        'model_name': 'claude-code-cli',
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

        # Check if file already exists with valid code
        file_ext = get_file_extension(language)
        output_file = output_dir / f"{prompt_id}.{file_ext}"

        # Check for exact match first
        if output_file.exists():
            try:
                existing_code = output_file.read_text()
                if existing_code.strip() and len(existing_code) > 50:  # Has substantial code
                    print(f"  ⏭️  Using cached (skipped)")
                    results['completed'] += 1
                    results['prompts'].append({
                        'id': prompt_id,
                        'category': category,
                        'language': language,
                        'output_file': str(output_file),
                        'success': True,
                        'code_length': len(existing_code),
                        'cached': True
                    })
                    continue
            except Exception as e:
                print(f"  ⚠️  Error reading existing file: {e}")

        # Check for any file with the same base name but different extension
        # This handles cases where the extension was corrected (e.g., .txt -> .swift, .cpp, .cs)
        found_alternative = False
        for existing in output_dir.glob(f"{prompt_id}.*"):
            if existing.is_file() and existing != output_file:
                try:
                    existing_code = existing.read_text()
                    if existing_code.strip() and len(existing_code) > 50:
                        print(f"  ⏭️  Already exists as {existing.name} (skipped)")
                        results['completed'] += 1
                        results['prompts'].append({
                            'id': prompt_id,
                            'category': category,
                            'language': language,
                            'output_file': str(existing),
                            'success': True,
                            'code_length': len(existing_code),
                            'cached': True
                        })
                        found_alternative = True
                        break
                except Exception as e:
                    print(f"  ⚠️  Error reading {existing.name}: {e}")

        if found_alternative:
            continue

        # Generate code with Claude Code
        code, success, failure_reason = generate_code_with_claude(prompt_text, timeout)

        if success and code:
            # Save to file (file_ext and output_file already defined above)

            with open(output_file, 'w') as f:
                f.write(code)

            print(f"  ✅ Saved to {output_file} ({len(code)} bytes)")
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
            print(f"  ❌ Failed")
            results['failed'] += 1
            results['prompts'].append({
                'id': prompt_id,
                'category': category,
                'language': language,
                'success': False,
                'error': 'Code generation failed',
                'failure_reason': failure_reason
            })

        # Small delay to avoid overwhelming the system
        time.sleep(1)

    elapsed = time.time() - start_time

    # Save results to reports directory (not in output_dir to avoid cluttering code directory)
    reports_dir = Path('reports')
    reports_dir.mkdir(parents=True, exist_ok=True)
    results_file = reports_dir / 'claude-code-cli_generation_results.json'
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)

    # Print summary
    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Model:          Claude Code CLI")
    print(f"Total prompts:  {results['total_prompts']}")
    print(f"Completed:      {results['completed']}")
    print(f"Failed:         {results['failed']}")
    print(f"Success rate:   {results['completed']/results['total_prompts']*100:.1f}%")
    print(f"Time elapsed:   {elapsed:.1f}s ({elapsed/len(prompts):.1f}s per prompt)")
    print(f"Results saved:  {results_file}")
    print("=" * 80)
    print()
    print("NEXT STEPS:")
    print(f"1. Run security tests: python3 runner.py --code-dir {output_dir} --model claude-code")
    print(f"2. View results: cat reports/claude-code_208point_*.json")
    print("3. Compare with Claude API baseline")
    print("=" * 80)

def main():
    parser = argparse.ArgumentParser(
        description='Test Claude Code CLI on security benchmark prompts'
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
        default=Path('output/claude-code'),
        help='Output directory (default: output/claude-code)'
    )
    parser.add_argument(
        '--timeout',
        type=int,
        default=600,
        help='Timeout per prompt in seconds (default: 600)'
    )
    parser.add_argument(
        '--limit',
        type=int,
        help='Limit number of prompts to test (for testing)'
    )
    parser.add_argument(
        '--check',
        action='store_true',
        help='Just check if Claude Code CLI is installed'
    )

    args = parser.parse_args()

    # Check installation
    if not check_claude_installed():
        return

    if args.check:
        print("✓ Claude Code CLI is installed and ready")
        return

    # Run benchmark
    test_claude_code_benchmark(
        args.prompts,
        args.output_dir,
        args.timeout,
        args.limit
    )

if __name__ == '__main__':
    main()
