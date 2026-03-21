#!/usr/bin/env python3
"""
Test OpenAI Codex models on security benchmark prompts.

Note: As of 2023, OpenAI deprecated the Codex API (code-davinci-002, code-cushman-001)
and replaced it with GPT-3.5-turbo and GPT-4 with code capabilities.

This script will attempt to use:
1. Legacy Codex models if available (code-davinci-002)
2. Fall back to gpt-3.5-turbo-instruct (similar to Codex)
3. Or use gpt-4 with code-focused prompting
"""

import os
import yaml
import subprocess
import argparse
import json
from pathlib import Path
from datetime import datetime
import time
import re

def check_codex_availability():
    """Check which Codex or Codex-like models are available."""
    try:
        import openai
        client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

        print("Checking available OpenAI models...")
        models = client.models.list()
        model_ids = [model.id for model in models.data]

        # Check for Codex models
        codex_models = [m for m in model_ids if 'code' in m.lower() or 'codex' in m.lower()]

        print(f"\nFound {len(codex_models)} code-related models:")
        for model in sorted(codex_models)[:10]:
            print(f"  - {model}")

        # Recommended models (in order of preference)
        candidates = [
            'gpt-5.3-codex',         # Latest GPT-5 Codex
            'gpt-5.2-codex',         # GPT-5.2 Codex
            'gpt-5.1-codex-max',     # GPT-5.1 Codex Max
            'gpt-5.1-codex',         # GPT-5.1 Codex
            'gpt-5-codex',           # Original GPT-5 Codex
            'code-davinci-002',      # Legacy Codex (deprecated)
            'gpt-3.5-turbo-instruct', # Closest to Codex behavior
            'gpt-4o-mini',           # Efficient code model
            'gpt-4o',                # Best quality
            'gpt-3.5-turbo'          # Fallback
        ]

        available = None
        for candidate in candidates:
            if candidate in model_ids:
                available = candidate
                print(f"\n✓ Will use: {candidate}")
                break

        if not available:
            print("\n⚠ No ideal Codex model found. Will try gpt-3.5-turbo as fallback.")
            available = 'gpt-3.5-turbo'

        return available

    except ImportError:
        print("ERROR: OpenAI package not installed")
        print("Install with: pip install openai")
        return None
    except Exception as e:
        print(f"ERROR: {e}")
        return None

def generate_code_with_openai(prompt: str, model: str, timeout: int = 60) -> tuple[str, bool]:
    """
    Generate code using OpenAI API.

    Returns:
        (code, success): The generated code and whether it succeeded
    """
    try:
        import openai
        client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

        # Different prompting strategies based on model type
        if 'codex' in model.lower() or 'instruct' in model or 'code-davinci' in model or 'code-cushman' in model:
            # Codex and instruction-following models use completions endpoint
            enhanced_prompt = f"{prompt}\n\nProvide only the complete, runnable code with no explanations."

            response = client.completions.create(
                model=model,
                prompt=enhanced_prompt,
                max_tokens=2048,
                temperature=0.2,
                top_p=1.0,
                frequency_penalty=0.0,
                presence_penalty=0.0,
                stop=["```", "###", "---", "\n\n\n"]
            )
            code = response.choices[0].text.strip()

        else:
            # Chat models need message format
            enhanced_prompt = f"{prompt}\n\nIMPORTANT: Output only the complete, runnable code. No explanations, descriptions, or markdown formatting. Just the raw code."

            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are an expert programmer. Generate only clean, runnable code without any explanations or markdown formatting."},
                    {"role": "user", "content": enhanced_prompt}
                ],
                max_tokens=2048,
                temperature=0.2
            )
            code = response.choices[0].message.content.strip()

        return code, True

    except Exception as e:
        print(f"    ❌ Error: {e}")
        return "", False

def extract_code_from_response(output: str, language: str) -> str:
    """
    Extract code from API response, handling markdown code blocks.
    """
    # Remove any markdown code blocks
    pattern = rf'```{language}\n(.*?)\n```'
    matches = re.findall(pattern, output, re.DOTALL | re.IGNORECASE)
    if matches:
        return matches[0].strip()

    # Try generic code blocks
    pattern = r'```\n(.*?)\n```'
    matches = re.findall(pattern, output, re.DOTALL)
    if matches:
        return matches[0].strip()

    # If no code blocks, return as-is (might already be clean code)
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
        'c': 'c',
        'cpp': 'cpp',
        'csharp': 'cs',
        'ruby': 'rb',
        'php': 'php',
    }
    return extensions.get(language, 'txt')

def test_codex_benchmark(prompts_file: Path, output_dir: Path, model: str, timeout: int = 60, limit: int = None):
    """
    Run Codex on all prompts in the benchmark.
    """
    # Load prompts
    with open(prompts_file) as f:
        data = yaml.safe_load(f)

    # Handle both formats
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
    print(f"CODEX/OpenAI BENCHMARK TEST")
    print("=" * 80)
    print(f"Model:        {model}")
    print(f"Prompts file: {prompts_file}")
    print(f"Output dir:   {output_dir}")
    print(f"Total prompts: {len(prompts)}")
    print(f"Timeout:      {timeout}s per prompt")
    print("=" * 80)
    print()

    # Results tracking
    results = {
        'benchmark_date': datetime.now().isoformat(),
        'model_name': model,
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

        # Generate code
        code, success = generate_code_with_openai(prompt_text, model, timeout)

        if success and code:
            # Extract clean code
            clean_code = extract_code_from_response(code, language)

            if clean_code:
                # Save to file
                file_ext = get_file_extension(language)
                output_file = output_dir / f"{prompt_id}.{file_ext}"

                with open(output_file, 'w') as f:
                    f.write(clean_code)

                print(f"  ✅ Saved to {output_file} ({len(clean_code)} bytes)")
                results['completed'] += 1

                results['prompts'].append({
                    'id': prompt_id,
                    'category': category,
                    'language': language,
                    'output_file': str(output_file),
                    'success': True,
                    'code_length': len(clean_code)
                })
            else:
                print(f"  ⚠️  No code extracted from response")
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
                'error': 'API call failed'
            })

        # Rate limiting - be nice to the API
        time.sleep(1)

    elapsed = time.time() - start_time

    # Save results summary
    results_file = output_dir / f'{model.replace("/", "_")}_generation_results.json'
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)

    # Print summary
    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Model:          {model}")
    print(f"Total prompts:  {results['total_prompts']}")
    print(f"Completed:      {results['completed']}")
    print(f"Failed:         {results['failed']}")
    print(f"Success rate:   {results['completed']/results['total_prompts']*100:.1f}%")
    print(f"Time elapsed:   {elapsed:.1f}s ({elapsed/len(prompts):.1f}s per prompt)")
    print(f"Results saved:  {results_file}")
    print("=" * 80)
    print()
    print("NEXT STEPS:")
    print(f"1. Run security tests: python3 runner.py --code-dir {output_dir} --model {model}")
    print(f"2. View results: cat reports/{model.replace('/', '_')}_208point_*.json")
    print("=" * 80)

def main():
    parser = argparse.ArgumentParser(
        description='Test OpenAI Codex/Code models on security benchmark prompts'
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
        default=Path('output/codex'),
        help='Output directory (default: output/codex)'
    )
    parser.add_argument(
        '--model',
        type=str,
        help='Specific OpenAI model to use (auto-detected if not specified)'
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
        '--check-models',
        action='store_true',
        help='Just check available models and exit'
    )

    args = parser.parse_args()

    # Check API key
    if not os.getenv('OPENAI_API_KEY'):
        print("ERROR: OPENAI_API_KEY environment variable not set")
        print("Set it with: export OPENAI_API_KEY='your-api-key'")
        return

    # Check available models
    if args.check_models:
        check_codex_availability()
        return

    # Auto-detect model if not specified
    model = args.model
    if not model:
        print("Auto-detecting best available Codex/code model...")
        model = check_codex_availability()
        if not model:
            print("ERROR: Could not find suitable model")
            return
        print()

    # Run benchmark
    test_codex_benchmark(
        args.prompts,
        args.output_dir,
        model,
        args.timeout,
        args.limit
    )

if __name__ == '__main__':
    main()
