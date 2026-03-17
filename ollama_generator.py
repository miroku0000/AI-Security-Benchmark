#!/usr/bin/env python3
"""
Ollama Code Generator

Automatically generates code using Ollama models for each prompt
in the benchmark and saves them for testing.
"""
import json
import subprocess
import yaml
import argparse
import time
import re
from pathlib import Path
from typing import Dict, List, Optional


class OllamaCodeGenerator:
    """Generate code using Ollama models."""

    def __init__(self, model: str = "codellama", temperature: float = 0.2):
        self.model = model
        self.temperature = temperature
        self.total_generated = 0
        self.failed_generations = []

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
        print("Attempting to start Ollama...")
        try:
            # Try to start Ollama in the background
            subprocess.Popen(
                ['ollama', 'serve'],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
            # Wait a few seconds for it to start
            import time
            time.sleep(3)

            # Check if it's running now
            if self.check_ollama():
                print("✅ Ollama started successfully")
                return True
            else:
                print("⚠️  Ollama may still be starting...")
                time.sleep(2)
                return self.check_ollama()
        except Exception as e:
            print(f"Failed to start Ollama: {e}")
            return False

    def list_models(self) -> List[str]:
        """List available Ollama models."""
        try:
            result = subprocess.run(
                ['ollama', 'list'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')[1:]  # Skip header
                models = [line.split()[0] for line in lines if line.strip()]
                return models
            return []
        except Exception as e:
            print(f"Error listing models: {e}")
            return []

    def generate_code(self, prompt: str, language: str) -> Optional[str]:
        """Generate code using Ollama."""
        # Enhance prompt to request just code
        enhanced_prompt = f"""Generate {language} code for the following requirement.
Provide only the code without explanations or markdown formatting.

Requirement: {prompt}

Code:"""

        try:
            # Call Ollama using subprocess
            result = subprocess.run(
                [
                    'ollama', 'run', self.model,
                    '--format', 'json' if False else '',  # Keep plain text for now
                ],
                input=enhanced_prompt,
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode == 0:
                code = result.stdout.strip()
                # Extract code from markdown if present
                code = self._extract_code(code, language)
                return code
            else:
                print(f"Error: {result.stderr}")
                return None

        except subprocess.TimeoutExpired:
            print(f"Timeout generating code for prompt")
            return None
        except Exception as e:
            print(f"Error generating code: {e}")
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
        print(f"Ollama Code Generator")
        print(f"{'='*70}")
        print(f"Model: {self.model}")
        print(f"Temperature: {self.temperature}")
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

            print(f"[{i}/{len(prompts)}] Generating {prompt_id} ({category}, {language})...")

            # Generate code
            code = self.generate_code(prompt_text, language)

            if code:
                # Save to file
                with open(output_file, 'w') as f:
                    f.write(f"# Generated by Ollama ({self.model})\n")
                    f.write(f"# Prompt: {prompt_text}\n")
                    f.write(f"# Category: {category}\n\n")
                    f.write(code)

                self.total_generated += 1
                print(f"  ✓ Saved to {output_file}")
            else:
                self.failed_generations.append(prompt_id)
                print(f"  ✗ Failed to generate code")

            # Small delay to avoid overwhelming Ollama
            time.sleep(0.5)

        # Summary
        print(f"\n{'='*70}")
        print(f"Generation Summary")
        print(f"{'='*70}")
        print(f"Successfully generated: {self.total_generated}/{len(prompts)}")
        print(f"Failed: {len(self.failed_generations)}")
        if self.failed_generations:
            print(f"Failed prompts: {', '.join(self.failed_generations)}")
        print(f"{'='*70}\n")


def main():
    parser = argparse.ArgumentParser(
        description="Generate code using Ollama for security benchmarking"
    )
    parser.add_argument(
        '--model',
        type=str,
        default='codellama',
        help='Ollama model to use (default: codellama)'
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
        '--list-models',
        action='store_true',
        help='List available Ollama models and exit'
    )

    args = parser.parse_args()

    generator = OllamaCodeGenerator(model=args.model, temperature=args.temperature)

    # Check Ollama is available
    if not generator.check_ollama():
        print("⚠️  Ollama is not running")
        print("Attempting to start Ollama automatically...")

        if not generator.start_ollama():
            print("\n❌ Could not start Ollama automatically")
            print("\nPlease:")
            print("1. Install Ollama from https://ollama.ai (if not installed)")
            print("2. Start Ollama manually: ollama serve")
            print("3. Or check if it's already running: ps aux | grep ollama")
            return 1

    # List models if requested
    if args.list_models:
        models = generator.list_models()
        print("Available Ollama models:")
        for model in models:
            print(f"  - {model}")
        return 0

    # Check if model exists
    available_models = generator.list_models()
    if args.model not in [m.split(':')[0] for m in available_models]:
        print(f"Warning: Model '{args.model}' not found in available models.")
        print(f"Available models: {', '.join(available_models)}")
        print(f"Proceeding anyway (Ollama will download if available)...")

    # Generate code
    generator.generate_from_prompts(
        args.prompts,
        args.output,
        limit=args.limit
    )

    return 0


if __name__ == "__main__":
    exit(main())
