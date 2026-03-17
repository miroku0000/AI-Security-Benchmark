#!/usr/bin/env python3
"""
Unified Code Generator

Supports multiple AI providers:
- Ollama (local models: codellama, deepseek-coder, etc.)
- OpenAI (gpt-4o, gpt-4-turbo, o1, o3, etc.)
- Anthropic Claude (claude-opus-4, claude-sonnet-4, etc.)
"""
import os
import json
import subprocess
import yaml
import argparse
import time
import re
from pathlib import Path
from typing import Dict, List, Optional
from cache_manager import CacheManager


class CodeGenerator:
    """Universal code generator supporting multiple AI providers."""

    def __init__(self, model: str, temperature: float = 0.2, use_cache: bool = True, force_regenerate: bool = False, timeout: int = None):
        self.model = model
        self.temperature = temperature
        self.total_generated = 0
        self.skipped_cached = 0
        self.failed_generations = []
        self.use_cache = use_cache
        self.force_regenerate = force_regenerate

        # Initialize cache manager
        if self.use_cache:
            self.cache = CacheManager()
        else:
            self.cache = None

        # Detect provider from model name
        self.provider = self._detect_provider(model)

        # Set intelligent default timeout based on provider
        if timeout is None:
            if self.provider == 'ollama':
                self.timeout = 300  # 5 minutes for Ollama (local models can be slow)
            else:
                self.timeout = 90  # 90 seconds for API-based models (OpenAI, Anthropic)
        else:
            self.timeout = timeout

        # Initialize provider-specific clients
        self._init_provider()

    def _detect_provider(self, model: str) -> str:
        """Detect provider from model name."""
        model_lower = model.lower()

        # OpenAI models (including latest: gpt-4o, gpt-5, o1, o3, chatgpt-4o-latest)
        if any(x in model_lower for x in ['gpt-3', 'gpt-4', 'gpt-5', 'o1', 'o3', 'chatgpt']):
            return 'openai'

        # Claude models (including opus-4, sonnet-4)
        if 'claude' in model_lower:
            return 'anthropic'

        # Default to Ollama for everything else
        return 'ollama'

    def _init_provider(self):
        """Initialize provider-specific clients."""
        if self.provider == 'openai':
            try:
                import openai
                self.openai_client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
                print(f"✅ OpenAI client initialized")
            except ImportError:
                print("❌ OpenAI package not installed. Install with: pip install openai")
                raise
            except Exception as e:
                print(f"❌ Failed to initialize OpenAI: {e}")
                print("Make sure OPENAI_API_KEY environment variable is set")
                raise

        elif self.provider == 'anthropic':
            try:
                import anthropic
                self.anthropic_client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
                print(f"✅ Anthropic client initialized")
            except ImportError:
                print("❌ Anthropic package not installed. Install with: pip install anthropic")
                raise
            except Exception as e:
                print(f"❌ Failed to initialize Anthropic: {e}")
                print("Make sure ANTHROPIC_API_KEY environment variable is set")
                raise

        elif self.provider == 'ollama':
            if not self.check_ollama():
                print("⚠️  Ollama is not running")
                print("Attempting to start Ollama automatically...")
                if not self.start_ollama():
                    print("\n❌ Could not start Ollama")
                    raise RuntimeError("Ollama not available")

    def check_ollama(self) -> bool:
        """Check if Ollama is installed and running."""
        try:
            result = subprocess.run(
                ['ollama', 'list'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def start_ollama(self) -> bool:
        """Attempt to start Ollama service."""
        try:
            subprocess.Popen(
                ['ollama', 'serve'],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
            time.sleep(3)
            if self.check_ollama():
                print("✅ Ollama started successfully")
                return True
            time.sleep(2)
            return self.check_ollama()
        except Exception as e:
            print(f"Failed to start Ollama: {e}")
            return False

    def generate_code(self, prompt: str, language: str) -> Optional[str]:
        """Generate code using the configured provider."""
        if self.provider == 'ollama':
            return self._generate_ollama(prompt, language)
        elif self.provider == 'openai':
            return self._generate_openai(prompt, language)
        elif self.provider == 'anthropic':
            return self._generate_anthropic(prompt, language)
        else:
            raise ValueError(f"Unknown provider: {self.provider}")

    def _generate_ollama(self, prompt: str, language: str) -> Optional[str]:
        """Generate code using Ollama."""
        enhanced_prompt = f"""Generate {language} code for the following requirement.
Provide only the code without explanations or markdown formatting.

Requirement: {prompt}

Code:"""

        try:
            result = subprocess.run(
                ['ollama', 'run', self.model],
                input=enhanced_prompt,
                capture_output=True,
                text=True,
                timeout=self.timeout
            )

            if result.returncode == 0:
                code = result.stdout.strip()
                return self._extract_code(code, language)
            else:
                print(f"Error: {result.stderr}")
                return None

        except subprocess.TimeoutExpired:
            print(f"Timeout generating code")
            return None
        except Exception as e:
            print(f"Error: {e}")
            return None

    def _generate_openai(self, prompt: str, language: str) -> Optional[str]:
        """Generate code using OpenAI."""
        system_prompt = f"""You are an expert {language} programmer. Generate code based on user requirements.
Provide only the code without explanations. Do not use markdown code blocks."""

        try:
            # GPT-5 series and o-series models use max_completion_tokens instead of max_tokens
            model_lower = self.model.lower()
            is_o_series = model_lower.startswith('o1') or model_lower.startswith('o3') or model_lower.startswith('o4')

            if 'gpt-5' in model_lower or is_o_series:
                # o-series models don't support custom temperature (only default 1.0)
                params = {
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    "max_completion_tokens": 4096
                }
                # Only add temperature for non-o-series models
                if not is_o_series:
                    params["temperature"] = self.temperature

                response = self.openai_client.chat.completions.create(**params)
            else:
                response = self.openai_client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=self.temperature,
                    max_tokens=4096
                )

            code = response.choices[0].message.content.strip()
            return self._extract_code(code, language)

        except Exception as e:
            print(f"Error: {e}")
            return None

    def _generate_anthropic(self, prompt: str, language: str) -> Optional[str]:
        """Generate code using Anthropic Claude."""
        system_prompt = f"""You are an expert {language} programmer. Generate code based on user requirements.
Provide only the code without explanations. Do not use markdown code blocks."""

        try:
            response = self.anthropic_client.messages.create(
                model=self.model,
                max_tokens=4096,
                temperature=self.temperature,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            code = response.content[0].text.strip()
            return self._extract_code(code, language)

        except Exception as e:
            print(f"Error: {e}")
            return None

    def _extract_code(self, response: str, language: str) -> str:
        """Extract code from response, handling markdown code blocks."""
        # Try to extract from markdown code blocks
        lang_pattern = f"```{language}\\s*\\n(.*?)```"
        match = re.search(lang_pattern, response, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()

        # Try generic code blocks
        generic_pattern = r"```\s*\n(.*?)```"
        match = re.search(generic_pattern, response, re.DOTALL)
        if match:
            return match.group(1).strip()

        # Try to extract code after "Code:" marker
        code_marker = re.search(r'Code:\s*\n(.*)', response, re.DOTALL | re.IGNORECASE)
        if code_marker:
            return code_marker.group(1).strip()

        # Return as-is if no markers found
        return response.strip()

    def generate_from_prompts(self, prompts_file: str, output_dir: str, limit: Optional[int] = None):
        """Generate code for all prompts in the file."""
        # Load prompts
        with open(prompts_file, 'r') as f:
            data = yaml.safe_load(f)
            prompts = data.get('prompts', [])

        if limit:
            prompts = prompts[:limit]

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        print(f"\n{'='*70}")
        print(f"AI Code Generator")
        print(f"{'='*70}")
        print(f"Provider: {self.provider}")
        print(f"Model: {self.model}")
        print(f"Temperature: {self.temperature}")
        print(f"Timeout: {self.timeout}s")
        print(f"Caching: {'Enabled' if self.use_cache else 'Disabled'}")
        if self.force_regenerate:
            print(f"Force Regenerate: Yes (ignoring cache)")
        print(f"Total prompts: {len(prompts)}")
        print(f"Output directory: {output_dir}")
        print(f"{'='*70}\n")

        for i, prompt_info in enumerate(prompts, 1):
            prompt_id = prompt_info['id']
            prompt_text = prompt_info['prompt']
            language = prompt_info.get('language', 'python')
            category = prompt_info['category']

            # Determine file extension
            extensions = {'python': '.py', 'javascript': '.js'}
            ext = extensions.get(language, '.txt')
            output_file = output_path / f"{prompt_id}{ext}"

            print(f"[{i}/{len(prompts)}] {prompt_id} ({category}, {language})...", end=' ')

            # Check cache if enabled
            if self.use_cache and not self.force_regenerate:
                if self.cache.is_cached(
                    self.model,
                    prompt_id,
                    prompt_text,
                    language,
                    category,
                    self.temperature,
                    output_file
                ):
                    print(f"✓ Using cached (skipped)")
                    self.skipped_cached += 1
                    continue

            print()  # New line before generation messages

            # Generate code
            code = self.generate_code(prompt_text, language)

            if code:
                # Save to file
                with open(output_file, 'w') as f:
                    f.write(f"# Generated by {self.provider} ({self.model})\n")
                    f.write(f"# Prompt: {prompt_text}\n")
                    f.write(f"# Category: {category}\n\n")
                    f.write(code)

                self.total_generated += 1
                print(f"  ✓ Saved to {output_file}")

                # Mark as generated in cache
                if self.use_cache:
                    self.cache.mark_generated(
                        self.model,
                        prompt_id,
                        prompt_text,
                        language,
                        category,
                        self.temperature,
                        output_file,
                        success=True
                    )
            else:
                self.failed_generations.append(prompt_id)
                print(f"  ✗ Failed to generate code")

                # Mark as failed in cache
                if self.use_cache:
                    self.cache.mark_generated(
                        self.model,
                        prompt_id,
                        prompt_text,
                        language,
                        category,
                        self.temperature,
                        output_file,
                        success=False
                    )

            # Small delay to avoid rate limiting
            if self.provider in ['openai', 'anthropic']:
                time.sleep(1)  # Be nice to API rate limits
            else:
                time.sleep(0.5)

        # Summary
        total_prompts = len(prompts)
        print(f"\n{'='*70}")
        print(f"Generation Summary")
        print(f"{'='*70}")
        print(f"Total prompts:        {total_prompts}")
        print(f"Newly generated:      {self.total_generated}")
        if self.use_cache:
            print(f"Skipped (cached):     {self.skipped_cached}")
        print(f"Failed:               {len(self.failed_generations)}")
        if self.failed_generations:
            print(f"\nFailed prompts: {', '.join(self.failed_generations)}")
        print(f"{'='*70}\n")


def main():
    parser = argparse.ArgumentParser(
        description="Generate code using AI models (Ollama, OpenAI, or Claude)",
        epilog="""
Examples:
  # Use latest OpenAI models with caching
  python3 code_generator.py --model gpt-4o
  python3 code_generator.py --model chatgpt-4o-latest

  # Use latest Claude models
  python3 code_generator.py --model claude-opus-4
  python3 code_generator.py --model claude-sonnet-4

  # Use Ollama models (automatic 5-minute timeout)
  python3 code_generator.py --model codellama
  python3 code_generator.py --model starcoder2:7b

  # Force regenerate everything (ignore cache)
  python3 code_generator.py --model gpt-4o --force-regenerate

  # Custom timeout for slow models
  python3 code_generator.py --model starcoder2:7b --timeout 600

  # Disable caching entirely
  python3 code_generator.py --model codellama --no-cache
        """
    )
    parser.add_argument(
        '--model',
        type=str,
        default='codellama',
        help='Model to use (e.g., gpt-4o, chatgpt-4o-latest, claude-opus-4, codellama)'
    )
    parser.add_argument(
        '--temperature',
        type=float,
        default=0.2,
        help='Temperature for generation (default: 0.2)'
    )
    parser.add_argument(
        '--prompts',
        type=str,
        default='prompts/prompts.yaml',
        help='Path to prompts file'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='generated',
        help='Output directory for generated code'
    )
    parser.add_argument(
        '--limit',
        type=int,
        help='Limit number of prompts to generate (for testing)'
    )
    parser.add_argument(
        '--no-cache',
        action='store_true',
        help='Disable caching (regenerate all code)'
    )
    parser.add_argument(
        '--force-regenerate',
        action='store_true',
        help='Force regenerate all code (ignore cache, but update it)'
    )
    parser.add_argument(
        '--timeout',
        type=int,
        default=None,
        help='Timeout in seconds for each generation (default: 300s for Ollama, 90s for API models)'
    )

    args = parser.parse_args()

    # Environment variable checks
    if any(x in args.model.lower() for x in ['gpt', 'chatgpt', 'o1', 'o3']) and not os.getenv('OPENAI_API_KEY'):
        print("❌ OPENAI_API_KEY environment variable not set")
        print("Set it with: export OPENAI_API_KEY='your-key-here'")
        return 1

    if 'claude' in args.model.lower() and not os.getenv('ANTHROPIC_API_KEY'):
        print("❌ ANTHROPIC_API_KEY environment variable not set")
        print("Set it with: export ANTHROPIC_API_KEY='your-key-here'")
        return 1

    try:
        generator = CodeGenerator(
            model=args.model,
            temperature=args.temperature,
            use_cache=not args.no_cache,
            force_regenerate=args.force_regenerate,
            timeout=args.timeout
        )
        generator.generate_from_prompts(
            args.prompts,
            args.output,
            limit=args.limit
        )
        return 0
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
