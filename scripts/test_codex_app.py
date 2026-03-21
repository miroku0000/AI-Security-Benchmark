#!/usr/bin/env python3
"""
Test Codex.app (OpenAI's desktop application) on security benchmark.

Codex.app uses GPT-5.4 by default but may add additional prompting/processing
on top of the base model, potentially affecting security performance.

This tests whether Codex.app performs differently than raw GPT-5.4 API.
"""

import yaml
import subprocess
import argparse
import json
from pathlib import Path
from datetime import datetime
import time
import re

CODEX_CLI = "/Applications/Codex.app/Contents/Resources/codex"

def check_codex_installed():
    """Check if Codex.app is installed and accessible."""
    codex_path = Path(CODEX_CLI)
    if not codex_path.exists():
        print(f"ERROR: Codex.app not found at {CODEX_CLI}")
        print("Please install Codex.app from OpenAI")
        return False

    try:
        result = subprocess.run(
            [CODEX_CLI, "--version"],
            capture_output=True,
            text=True,
            timeout=10
        )
        print(f"✓ Found Codex.app: {result.stdout.strip() or result.stderr.strip()}")
        return True
    except Exception as e:
        print(f"ERROR: Could not run Codex CLI: {e}")
        return False

def generate_code_with_codex(prompt: str, model: str = None, timeout: int = 120) -> tuple[str, bool]:
    """
    Generate code using Codex.app CLI.

    Returns:
        (code, success): The generated code and whether it succeeded
    """
    try:
        # Build command
        cmd = [
            CODEX_CLI,
            "exec",
            "--sandbox", "read-only",  # Safe mode - no file writes
        ]

        # Add model if specified
        if model:
            cmd.extend(["-m", model])

        # Enhanced prompt to get code only
        enhanced_prompt = f"{prompt}\n\nIMPORTANT: Output ONLY the complete, runnable code. No explanations, descriptions, or markdown. Just the raw code file contents."
        cmd.append(enhanced_prompt)

        # Run codex exec
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd="."
        )

        if result.returncode == 0:
            output = result.stdout.strip()

            # Codex may still include explanatory text
            # Try to extract just the code
            code = extract_code_from_output(output)

            if code:
                return code, True
            else:
                print(f"    ⚠️  No code extracted (got {len(output)} chars)")
                return output, False
        else:
            error = result.stderr.strip()
            print(f"    ⚠️  Codex returned error: {error[:100]}")
            return "", False

    except subprocess.TimeoutExpired:
        print(f"    ⚠️  Timeout after {timeout}s")
        return "", False
    except Exception as e:
        print(f"    ❌ Error: {e}")
        return "", False

def extract_code_from_output(output: str) -> str:
    """
    Extract code from Codex output.
    Codex may include explanatory text before/after code.
    """
    # Try to find code blocks first
    code_block_pattern = r'```(?:\w+)?\n(.*?)\n```'
    matches = re.findall(code_block_pattern, output, re.DOTALL)
    if matches:
        return matches[0].strip()

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
    }
    return extensions.get(language, 'txt')

def test_codex_app_benchmark(
    prompts_file: Path,
    output_dir: Path,
    model: str = None,
    timeout: int = 120,
    limit: int = None
):
    """
    Run Codex.app on all prompts in the benchmark.
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
    print(f"CODEX.APP BENCHMARK TEST")
    print("=" * 80)
    print(f"Model:        {model or 'default (GPT-5.4)'}")
    print(f"Prompts file: {prompts_file}")
    print(f"Output dir:   {output_dir}")
    print(f"Total prompts: {len(prompts)}")
    print(f"Timeout:      {timeout}s per prompt")
    print("=" * 80)
    print()

    # Results tracking
    results = {
        'benchmark_date': datetime.now().isoformat(),
        'model_name': f'codex-app-{model}' if model else 'codex-app-gpt-5.4',
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

        # Generate code with Codex.app
        code, success = generate_code_with_codex(prompt_text, model, timeout)

        if success and code:
            # Save to file
            file_ext = get_file_extension(language)
            output_file = output_dir / f"{prompt_id}.{file_ext}"

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
                'error': 'Code generation failed'
            })

        # Small delay to avoid overwhelming the system
        time.sleep(2)

    elapsed = time.time() - start_time

    # Save results
    model_name = model or 'gpt-5.4'
    results_file = output_dir / f'codex-app-{model_name.replace("/", "_")}_generation_results.json'
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)

    # Print summary
    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Model:          {model or 'default (GPT-5.4)'}")
    print(f"Total prompts:  {results['total_prompts']}")
    print(f"Completed:      {results['completed']}")
    print(f"Failed:         {results['failed']}")
    print(f"Success rate:   {results['completed']/results['total_prompts']*100:.1f}%")
    print(f"Time elapsed:   {elapsed:.1f}s ({elapsed/len(prompts):.1f}s per prompt)")
    print(f"Results saved:  {results_file}")
    print("=" * 80)
    print()
    print("NEXT STEPS:")
    print(f"1. Run security tests: python3 runner.py --code-dir {output_dir} --model codex-app")
    print(f"2. View results: cat reports/codex-app_208point_*.json")
    print("3. Compare with GPT-5.4 API baseline (134/208, 64.4%)")
    print("=" * 80)

def main():
    parser = argparse.ArgumentParser(
        description='Test Codex.app on security benchmark prompts'
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
        default=Path('output/codex-app'),
        help='Output directory (default: output/codex-app)'
    )
    parser.add_argument(
        '--model',
        type=str,
        help='Model to use (default: GPT-5.4)'
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
    parser.add_argument(
        '--check',
        action='store_true',
        help='Just check if Codex.app is installed'
    )

    args = parser.parse_args()

    # Check installation
    if not check_codex_installed():
        return

    if args.check:
        print("✓ Codex.app is installed and ready")
        return

    # Run benchmark
    test_codex_app_benchmark(
        args.prompts,
        args.output_dir,
        args.model,
        args.timeout,
        args.limit
    )

if __name__ == '__main__':
    main()
