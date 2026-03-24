#!/usr/bin/env python3
"""
Test Codex.app with Security Best Practice Skill explicitly activated.

This version modifies prompts to explicitly trigger the security-best-practices skill.
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

def generate_code_with_codex(prompt: str, model: str = None, timeout: int = 120) -> tuple[str, bool, str]:
    """
    Generate code using Codex.app CLI with security skill explicitly triggered.

    Returns:
        (code, success, failure_reason): The generated code, whether it succeeded, and reason for failure
    """
    try:
        # Build command
        cmd = [
            CODEX_CLI,
            "exec",
            "--sandbox", "read-only",  # Safe mode - no file writes
            "--skip-git-repo-check",  # Allow running from /tmp (needed for underscore bug workaround)
        ]

        # Add model if specified
        if model:
            cmd.extend(["-m", model])

        # Enhanced prompt that explicitly triggers security best practices skill
        # Based on SKILL.md: "Trigger only when the user explicitly requests security best practices guidance"
        # Must explicitly name the skill to activate it
        enhanced_prompt = f"""Use the security-best-practices skill to write secure-by-default code for the following requirement:

{prompt}

Apply security best practices to prevent common vulnerabilities. Output ONLY the complete, runnable code. No explanations or markdown."""

        cmd.append(enhanced_prompt)

        # Run codex exec
        # Use /tmp as working directory to avoid CLI bug with underscores in path
        # (Codex v0.116.0-alpha.10 has a bug with underscore in directory names)
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd="/tmp"
        )

        if result.returncode == 0:
            output = result.stdout.strip()

            # Codex may still include explanatory text
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
            print(f"    ⚠️  Codex returned error: {error[:100]}")
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
        'cpp': 'cpp',
        'c++': 'cpp',
        'csharp': 'cs',
        'c#': 'cs',
    }
    return extensions.get(language.lower(), 'txt')

def test_codex_app_benchmark(
    prompts_file: Path,
    output_dir: Path,
    model: str = None,
    timeout: int = 120,
    limit: int = None
):
    """
    Run Codex.app on all prompts with security skill explicitly triggered.
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
    print(f"CODEX.APP SECURITY SKILL BENCHMARK TEST")
    print("=" * 80)
    print(f"Model:        {model or 'default (GPT-5.4)'}")
    print(f"Skill:        Security Best Practices (EXPLICIT TRIGGER)")
    print(f"Prompts file: {prompts_file}")
    print(f"Output dir:   {output_dir}")
    print(f"Total prompts: {len(prompts)}")
    print(f"Timeout:      {timeout}s per prompt")
    print("=" * 80)
    print()

    # Results tracking
    results = {
        'benchmark_date': datetime.now().isoformat(),
        'model_name': f'codex-app-security-skill-{model}' if model else 'codex-app-security-skill',
        'security_skill_enabled': True,
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

        # Generate code with Codex.app + security skill
        code, success, failure_reason = generate_code_with_codex(prompt_text, model, timeout)

        if success and code:
            # Save to file
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
        time.sleep(2)

    elapsed = time.time() - start_time

    # Save results to reports directory (not in output_dir to avoid cluttering code directory)
    model_name = model or 'gpt-5.4'
    reports_dir = Path('reports')
    reports_dir.mkdir(parents=True, exist_ok=True)
    results_file = reports_dir / f'codex-app-security-skill-{model_name.replace("/", "_")}_generation_results.json'
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)

    # Print summary
    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Model:          {model or 'default (GPT-5.4)'}")
    print(f"Skill:          Security Best Practices (EXPLICIT)")
    print(f"Total prompts:  {results['total_prompts']}")
    print(f"Completed:      {results['completed']}")
    print(f"Failed:         {results['failed']}")
    print(f"Success rate:   {results['completed']/results['total_prompts']*100:.1f}%")
    print(f"Time elapsed:   {elapsed:.1f}s ({elapsed/len(prompts):.1f}s per prompt)")
    print(f"Results saved:  {results_file}")
    print("=" * 80)
    print()
    print("NEXT STEPS:")
    print(f"1. Run security tests: python3 runner.py --code-dir {output_dir} --model codex-app-security-skill")
    print(f"2. View results: cat reports/codex-app-security-skill_208point_*.json")
    print("3. Compare with baseline (without skill)")
    print("=" * 80)

def main():
    parser = argparse.ArgumentParser(
        description='Test Codex.app with Security Best Practices Skill'
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
        default=Path('output/codex-app-security-skill'),
        help='Output directory (default: output/codex-app-security-skill)'
    )
    parser.add_argument(
        '--model',
        type=str,
        help='Model to use (default: GPT-5.4)'
    )
    parser.add_argument(
        '--timeout',
        type=int,
        default=300,
        help='Timeout per prompt in seconds (default: 300)'
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
        print("NOTE: Security Best Practices skill will be triggered via prompt")
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
