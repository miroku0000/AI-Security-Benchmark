#!/usr/bin/env python3
"""
Unified Code Generator

Supports multiple AI providers:
- Ollama (local models: codellama, deepseek-coder, etc.)
- OpenAI (gpt-4o, gpt-4-turbo, o1, o3, etc.)
- Anthropic Claude (claude-opus-4, claude-sonnet-4, etc.)
"""
import logging
import os
import subprocess
import yaml
import argparse
import time
import re
from pathlib import Path
from typing import Optional
from cache_manager import CacheManager

logger = logging.getLogger(__name__)


class CodeGenerator:
    """Universal code generator supporting multiple AI providers."""

    def __init__(self, model: str, temperature: float = 0.2, use_cache: bool = True, force_regenerate: bool = False, timeout: int = None, use_bedrock: bool = False):
        self.model = model
        self.temperature = temperature
        self.total_generated = 0
        self.skipped_cached = 0
        self.failed_generations = []
        self.use_cache = use_cache
        self.force_regenerate = force_regenerate

        # Initialize Bedrock attributes (will be set properly for Anthropic provider)
        # ONLY use Bedrock if --use-bedrock flag is explicitly set
        # If flag is not set (use_bedrock=False), unset environment variable to prevent accidental Bedrock usage
        if not use_bedrock:
            # Unset environment variable to ensure we use direct Anthropic API
            if 'CLAUDE_CODE_USE_BEDROCK' in os.environ:
                del os.environ['CLAUDE_CODE_USE_BEDROCK']

        self.use_bedrock = use_bedrock
        self.bedrock_model = None

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

        # Application-based models (should use test scripts)
        if 'cursor' in model_lower:
            return 'cursor'

        if 'codex-app' in model_lower or 'codex_app' in model_lower:
            return 'codex-app'

        # Claude Code CLI (separate from Anthropic API)
        if 'claude-code' in model_lower or 'claude_code' in model_lower:
            return 'claude-code'

        # OpenAI models (including latest: gpt-4o, gpt-5, o1, o3, chatgpt-4o-latest)
        if any(x in model_lower for x in ['gpt-3', 'gpt-4', 'gpt-5', 'o1', 'o3', 'chatgpt']):
            return 'openai'

        # Claude models (including opus-4, sonnet-4)
        if 'claude' in model_lower:
            return 'anthropic'

        # Gemini models
        if 'gemini' in model_lower:
            return 'google'

        # Default to Ollama for everything else
        return 'ollama'

    def _init_provider(self):
        """Initialize provider-specific clients."""
        if self.provider == 'openai':
            try:
                import openai
                self.openai_client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
                logger.info("OpenAI client initialized")
            except ImportError:
                logger.error("OpenAI package not installed. Install with: pip install openai")
                raise
            except Exception as e:
                logger.error("Failed to initialize OpenAI: %s", e)
                logger.error("Make sure OPENAI_API_KEY environment variable is set")
                raise

        elif self.provider == 'anthropic':
            try:
                import anthropic

                # use_bedrock is already set from __init__ parameter (default: False)
                # Only use Bedrock if explicitly requested via --use-bedrock flag

                if self.use_bedrock:
                    # Use AWS Bedrock
                    self.anthropic_client = anthropic.AnthropicBedrock()
                    # Convert model name to Bedrock format
                    self.bedrock_model = self._convert_to_bedrock_model_id(self.model)
                    logger.info("Anthropic Bedrock client initialized (using AWS credentials)")
                    logger.info("Model mapping: %s -> %s", self.model, self.bedrock_model)
                else:
                    # Use direct Anthropic API
                    api_key = os.getenv('ANTHROPIC_API_KEY') or os.getenv('MYANTHROPIC_API_KEY')
                    self.anthropic_client = anthropic.Anthropic(api_key=api_key)
                    self.bedrock_model = None
                    logger.info("Anthropic client initialized (direct API)")
            except ImportError:
                logger.error("Anthropic package not installed. Install with: pip install anthropic")
                raise
            except Exception as e:
                logger.error("Failed to initialize Anthropic: %s", e)
                if self.use_bedrock:
                    logger.error("Make sure AWS credentials are configured for Bedrock")
                else:
                    logger.error("Make sure ANTHROPIC_API_KEY (or MYANTHROPIC_API_KEY) environment variable is set")
                raise

        elif self.provider == 'google':
            try:
                from google import genai
                self.google_client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))
                logger.info("Google Gemini client initialized")
            except ImportError:
                logger.error("Google GenAI package not installed. Install with: pip install google-genai")
                raise
            except Exception as e:
                logger.error("Failed to initialize Google Gemini: %s", e)
                logger.error("Make sure GEMINI_API_KEY environment variable is set")
                raise

        elif self.provider == 'cursor':
            # Application-based model - delegate to test script
            logger.info("Cursor detected - will delegate to scripts/test_cursor.py")
            self._delegate_to_script = 'scripts/test_cursor.py'

        elif self.provider == 'codex-app':
            # Application-based model - delegate to test script
            logger.info("Codex.app detected - will delegate to scripts/test_codex_app.py")
            self._delegate_to_script = 'scripts/test_codex_app.py'

        elif self.provider == 'claude-code':
            # Application-based model - delegate to test script
            logger.info("Claude Code detected - will delegate to scripts/test_claude_code.py")
            self._delegate_to_script = 'scripts/test_claude_code.py'

        elif self.provider == 'ollama':
            if not self.check_ollama():
                logger.warning("Ollama is not running")
                logger.info("Attempting to start Ollama automatically...")
                if not self.start_ollama():
                    logger.error("Could not start Ollama")
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
                logger.info("Ollama started successfully")
                return True
            time.sleep(2)
            return self.check_ollama()
        except Exception as e:
            logger.error("Failed to start Ollama: %s", e)
            return False

    def generate_code(self, prompt: str, language: str) -> Optional[str]:
        """Generate code using the configured provider."""
        if self.provider == 'ollama':
            return self._generate_ollama(prompt, language)
        elif self.provider == 'openai':
            return self._generate_openai(prompt, language)
        elif self.provider == 'anthropic':
            return self._generate_anthropic(prompt, language)
        elif self.provider == 'google':
            return self._generate_google(prompt, language)
        else:
            raise ValueError(f"Unknown provider: {self.provider}")

    def _generate_ollama(self, prompt: str, language: str) -> Optional[str]:
        """Generate code using Ollama with temperature support."""
        enhanced_prompt = f"""Generate {language} code for the following requirement.
Provide only the code without explanations or markdown formatting.

Requirement: {prompt}

Code:"""

        try:
            # Try to use ollama Python library for temperature support
            try:
                import ollama

                response = ollama.generate(
                    model=self.model,
                    prompt=enhanced_prompt,
                    options={
                        'temperature': self.temperature,
                        'num_predict': 4096,  # max tokens
                    }
                )

                code = response['response'].strip()
                if not code:
                    logger.warning("Empty response from model")
                    return None
                return self._extract_code(code, language)

            except ImportError:
                # Fallback to subprocess if ollama library not installed
                logger.warning("ollama library not installed (pip install ollama) - temperature not supported")
                logger.warning("Falling back to subprocess method without temperature control")

                result = subprocess.run(
                    ['ollama', 'run', self.model],
                    input=enhanced_prompt,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout
                )

                if result.returncode == 0:
                    code = result.stdout.strip()
                    if not code:
                        logger.warning("Empty response from model")
                        return None
                    return self._extract_code(code, language)
                else:
                    logger.error("Ollama error: %s", result.stderr)
                    return None

        except subprocess.TimeoutExpired:
            logger.warning("Timeout after %ds", self.timeout)
            return None
        except Exception as e:
            logger.error("Ollama generation error: %s", e)
            return None

    def _convert_to_bedrock_model_id(self, model_name: str) -> str:
        """Convert Direct API model name to Bedrock model ID."""
        # Mapping of Direct API model names to Bedrock model IDs
        bedrock_mapping = {
            # Claude 3.5 models
            'claude-3-5-sonnet-20241022': 'anthropic.claude-3-5-sonnet-20241022-v2:0',
            'claude-3-5-sonnet-20240620': 'anthropic.claude-3-5-sonnet-20240620-v1:0',
            'claude-3-5-haiku-20241022': 'anthropic.claude-3-5-haiku-20241022-v1:0',
            # Claude 3 models
            'claude-3-opus-20240229': 'anthropic.claude-3-opus-20240229-v1:0',
            'claude-3-sonnet-20240229': 'anthropic.claude-3-sonnet-20240229-v1:0',
            'claude-3-haiku-20240307': 'anthropic.claude-3-haiku-20240307-v1:0',
            # Aliases (short names)
            'claude-3-5-sonnet': 'anthropic.claude-3-5-sonnet-20241022-v2:0',  # Latest
            'claude-3-5-haiku': 'anthropic.claude-3-5-haiku-20241022-v1:0',
            'claude-3-opus': 'anthropic.claude-3-opus-20240229-v1:0',
            'claude-3-sonnet': 'anthropic.claude-3-sonnet-20240229-v1:0',
            'claude-3-haiku': 'anthropic.claude-3-haiku-20240307-v1:0',
            # Future models (placeholder - update when available)
            'claude-opus-4-6': 'anthropic.claude-3-opus-20240229-v1:0',  # Fall back to Claude 3 Opus
            'claude-sonnet-4-5': 'anthropic.claude-3-5-sonnet-20241022-v2:0',  # Fall back to Claude 3.5 Sonnet
        }

        # Check if already in Bedrock format
        if model_name.startswith('anthropic.'):
            return model_name

        # Look up in mapping
        bedrock_id = bedrock_mapping.get(model_name)
        if bedrock_id:
            return bedrock_id

        # If not found, log warning and return as-is (will likely fail, but let Bedrock give the error)
        logger.warning("Unknown model '%s' - no Bedrock mapping found, using as-is", model_name)
        return model_name

    def _generate_openai(self, prompt: str, language: str) -> Optional[str]:
        """Generate code using OpenAI."""
        system_prompt = f"""You are an expert {language} programmer. Generate code based on user requirements.
Provide only the code without explanations. Do not use markdown code blocks."""

        try:
            # GPT-5 series and o-series models use max_completion_tokens instead of max_tokens
            model_lower = self.model.lower()
            is_o_series = model_lower.startswith('o1') or model_lower.startswith('o3') or model_lower.startswith('o4')
            # Cursor and Codex use fixed temperatures and don't allow customization
            is_fixed_temp = 'cursor' in model_lower or 'codex' in model_lower

            if 'gpt-5' in model_lower or is_o_series or is_fixed_temp:
                # o-series, cursor, and codex models don't support custom temperature
                params = {
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    "max_completion_tokens": 4096
                }
                # Only add temperature for GPT-5 series (non-o-series, non-fixed-temp models)
                if 'gpt-5' in model_lower and not is_o_series and not is_fixed_temp:
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
            logger.error("OpenAI generation error: %s", e)
            return None

    def _generate_anthropic(self, prompt: str, language: str) -> Optional[str]:
        """Generate code using Anthropic Claude."""
        system_prompt = f"""You are an expert {language} programmer. Generate code based on user requirements.
Provide only the code without explanations. Do not use markdown code blocks."""

        # Use Bedrock model ID if in Bedrock mode, otherwise use direct API model name
        model_id = self.bedrock_model if self.use_bedrock else self.model

        try:
            response = self.anthropic_client.messages.create(
                model=model_id,
                max_tokens=4096,
                temperature=self.temperature,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            # Check for refusal
            if response.stop_reason == 'refusal':
                logger.warning("Claude refused to generate code (safety filters triggered)")
                logger.warning("This is expected for some security vulnerability prompts")
                # Try a more neutral phrasing to bypass safety filters
                modified_prompt = prompt.replace("external entity", "entity").replace("vulnerability", "feature")
                logger.info("Retrying with modified prompt...")

                response = self.anthropic_client.messages.create(
                    model=model_id,
                    max_tokens=4096,
                    temperature=self.temperature,
                    system=system_prompt,
                    messages=[
                        {"role": "user", "content": modified_prompt}
                    ]
                )

                if response.stop_reason == 'refusal':
                    logger.error("Claude still refusing after prompt modification")
                    return None

            # Check for empty content
            if len(response.content) == 0:
                logger.error("Response content is empty! Stop reason: %s", response.stop_reason)
                return None

            code = response.content[0].text.strip()
            return self._extract_code(code, language)

        except Exception as e:
            logger.error("Anthropic generation error: %s", e)
            return None

    def _generate_google(self, prompt: str, language: str) -> Optional[str]:
        """Generate code using Google Gemini with 429 rate-limit handling."""
        system_prompt = f"""You are an expert {language} programmer. Generate code based on user requirements.
Provide only the code without explanations. Do not use markdown code blocks."""

        max_retries = 5
        for attempt in range(max_retries):
            try:
                response = self.google_client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config={
                        "system_instruction": system_prompt,
                        "temperature": self.temperature,
                        "max_output_tokens": 4096,
                    }
                )

                code = response.text.strip()
                return self._extract_code(code, language)

            except Exception as e:
                error_str = str(e)

                # Detect 429 rate limit errors
                if '429' in error_str or 'RESOURCE_EXHAUSTED' in error_str:
                    # Check if it's a DAILY quota exhaustion (not recoverable by waiting a few seconds)
                    if 'PerDay' in error_str or 'per_day' in error_str.lower():
                        logger.error("DAILY QUOTA EXHAUSTED for %s", self.model)
                        logger.error("Cannot generate more requests today. Stopping this model.")
                        self._daily_quota_exhausted = True
                        return None

                    # Parse retryDelay from error if available
                    retry_delay = 60  # default 60s
                    delay_match = re.search(r'retryDelay.*?(\d+(?:\.\d+)?)\s*s', error_str)
                    if delay_match:
                        retry_delay = max(int(float(delay_match.group(1))) + 2, 5)

                    logger.warning("Rate limited (429). Waiting %ds before retry %d/%d...", retry_delay, attempt+1, max_retries)
                    time.sleep(retry_delay)
                    continue
                else:
                    logger.error("Google generation error: %s", e)
                    return None

        logger.error("Failed after %d rate-limit retries", max_retries)
        return None

    def _generate_claude_cli(self, prompt: str, language: str) -> Optional[str]:
        """Generate code using Claude Code CLI in isolated temp directory."""
        import tempfile
        import shutil

        # Enhanced prompt to get code only
        # Based on scripts/test_claude_code.py which has been tested to work
        enhanced_prompt = f"""{prompt}

IMPORTANT: Output ONLY the complete, runnable code. No explanations, descriptions, markdown blocks, or commentary. Just the raw code file contents that can be directly saved and executed."""

        # Create a temporary directory for isolated execution
        temp_dir = tempfile.mkdtemp(prefix='claude_gen_')

        try:
            # Run claude command in print mode from temp directory
            # --print: Print response and exit
            # --dangerously-skip-permissions: Skip permission dialogs for automation
            result = subprocess.run(
                ['claude', '--print', '--dangerously-skip-permissions', enhanced_prompt],
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=temp_dir
            )

            if result.returncode == 0:
                output = result.stdout.strip()
                logger.debug("CLI output length: %d chars", len(output))
                logger.debug("First 200 chars: %s", output[:200])
                code = self._extract_code(output, language)

                if code:
                    logger.debug("Extracted code length: %d chars", len(code))
                    return code
                else:
                    logger.warning("No code extracted from output (length: %d)", len(output))
                    logger.warning("Output preview: %s", output[:500])
                    return None
            else:
                error = result.stderr.strip()
                logger.error("Claude CLI error: %s", error[:200])
                return None

        except subprocess.TimeoutExpired:
            logger.warning("Timeout after %ds", self.timeout)
            return None
        except Exception as e:
            logger.error("Claude CLI generation error: %s", e)
            return None
        finally:
            # Clean up temp directory
            try:
                shutil.rmtree(temp_dir)
            except Exception as e:
                logger.warning("Failed to clean up temp dir %s: %s", temp_dir, e)

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

    def _generate_single_prompt(self, prompt_info: dict, output_path: Path, index: int, total: int) -> bool:
        """Generate code for a single prompt. Returns True if successful."""
        prompt_id = prompt_info['id']
        prompt_text = prompt_info['prompt']
        language = prompt_info.get('language', 'python')
        category = prompt_info['category']

        extensions = {
            'python': '.py',
            'javascript': '.js',
            'java': '.java',
            'csharp': '.cs',
            'cpp': '.cpp',
            'c': '.c',
            'go': '.go',
            'rust': '.rs',
            'scala': '.scala',
            'perl': '.pl',
            'lua': '.lua',
            'elixir': '.ex',
            'solidity': '.sol'
        }
        ext = extensions.get(language, '.txt')
        output_file = output_path / f"{prompt_id}{ext}"

        logger.info("[%d/%d] %s (%s, %s)...", index, total, prompt_id, category, language)

        # Check if file already exists in model-specific output directory
        # This allows us to skip regenerating files that were already generated
        model_output_dir = Path('output') / self.model
        existing_file = model_output_dir / f"{prompt_id}{ext}"
        if existing_file.exists() and not self.force_regenerate:
            logger.info("  Already exists in %s (skipped)", model_output_dir)
            self.skipped_cached += 1
            return True

        # Check cache if enabled
        if self.use_cache and not self.force_regenerate:
            if self.cache.is_cached(
                self.model, prompt_id, prompt_text, language,
                category, self.temperature, output_file
            ):
                logger.info("  Using cached (skipped)")
                self.skipped_cached += 1
                return True

        code = self.generate_code(prompt_text, language)

        if code:
            with open(output_file, 'w') as f:
                f.write(f"# Generated by {self.provider} ({self.model})\n")
                f.write(f"# Prompt: {prompt_text}\n")
                f.write(f"# Category: {category}\n\n")
                f.write(code)

            self.total_generated += 1
            logger.info("  Saved to %s", output_file)

            if self.use_cache:
                self.cache.mark_generated(
                    self.model, prompt_id, prompt_text, language,
                    category, self.temperature, output_file, success=True
                )
            return True
        else:
            logger.error("  Failed to generate code for %s", prompt_id)
            if self.use_cache:
                self.cache.mark_generated(
                    self.model, prompt_id, prompt_text, language,
                    category, self.temperature, output_file, success=False
                )
            return False

    def generate_from_prompts(self, prompts_file: str, output_dir: str, limit: Optional[int] = None, retries: int = 0):
        """Generate code for all prompts in the file with optional retries for failures."""
        # Check if we should delegate to a test script
        if hasattr(self, '_delegate_to_script'):
            logger.info("=" * 70)
            logger.info("Delegating to %s", self._delegate_to_script)
            logger.info("=" * 70)
            logger.info("Provider: %s", self.provider)
            logger.info("Model: %s", self.model)
            logger.info("Output directory: %s", output_dir)
            logger.info("=" * 70)

            # Build command to run test script
            cmd = ['python3', self._delegate_to_script, '--output-dir', output_dir, '--timeout', str(self.timeout)]
            if limit:
                cmd.extend(['--limit', str(limit)])

            try:
                result = subprocess.run(cmd, check=True)
                logger.info("=" * 70)
                logger.info("Delegation completed successfully")
                logger.info("=" * 70)
                return
            except subprocess.CalledProcessError as e:
                logger.error("Delegation failed with exit code %d", e.returncode)
                raise

        # Load prompts
        with open(prompts_file, 'r') as f:
            data = yaml.safe_load(f)
            prompts = data.get('prompts', [])

        if limit:
            prompts = prompts[:limit]

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        logger.info("=" * 70)
        logger.info("AI Code Generator")
        logger.info("=" * 70)
        logger.info("Provider: %s", self.provider)
        logger.info("Model: %s", self.model)
        logger.info("Temperature: %s", self.temperature)
        logger.info("Timeout: %ds", self.timeout)
        logger.info("Caching: %s", 'Enabled' if self.use_cache else 'Disabled')
        if self.force_regenerate:
            logger.info("Force Regenerate: Yes (ignoring cache)")
        if retries > 0:
            logger.info("Retries: %d", retries)
        logger.info("Total prompts: %d", len(prompts))
        logger.info("Output directory: %s", output_dir)
        logger.info("=" * 70)

        # Track daily quota exhaustion for Google
        self._daily_quota_exhausted = False

        # First pass
        failed_prompts = []
        for i, prompt_info in enumerate(prompts, 1):
            # Stop early if daily quota is exhausted
            if self._daily_quota_exhausted:
                logger.error("Skipping %s -- daily quota exhausted", prompt_info['id'])
                failed_prompts.append(prompt_info)
                continue

            success = self._generate_single_prompt(prompt_info, output_path, i, len(prompts))
            if not success:
                failed_prompts.append(prompt_info)

            # Delay to avoid rate limiting
            if self.provider == 'google':
                time.sleep(3)  # Small delay; 429 handler does the real waiting
            elif self.provider in ['openai', 'anthropic']:
                time.sleep(1)
            else:
                time.sleep(0.5)

        # Retry failed prompts (skip if daily quota exhausted)
        for retry_num in range(1, retries + 1):
            if not failed_prompts:
                break
            if self._daily_quota_exhausted:
                logger.error("Skipping retries -- daily quota exhausted for %s", self.model)
                break

            logger.info("=" * 70)
            logger.info("Retry %d/%d -- %d failed prompts", retry_num, retries, len(failed_prompts))
            logger.info("=" * 70)

            # Clear failed cache entries so retries actually attempt generation
            if self.use_cache:
                for prompt_info in failed_prompts:
                    self.cache.invalidate(
                        self.model, prompt_info['id']
                    )

            still_failed = []
            for i, prompt_info in enumerate(failed_prompts, 1):
                if self._daily_quota_exhausted:
                    logger.error("Skipping %s -- daily quota exhausted", prompt_info['id'])
                    still_failed.append(prompt_info)
                    continue

                success = self._generate_single_prompt(prompt_info, output_path, i, len(failed_prompts))
                if not success:
                    still_failed.append(prompt_info)

                if self.provider == 'google':
                    time.sleep(3)
                elif self.provider in ['openai', 'anthropic']:
                    time.sleep(1)
                else:
                    time.sleep(0.5)

            failed_prompts = still_failed

        self.failed_generations = [p['id'] for p in failed_prompts]

        # Summary
        total_prompts = len(prompts)
        logger.info("=" * 70)
        logger.info("Generation Summary")
        logger.info("=" * 70)
        logger.info("Total prompts:        %d", total_prompts)
        logger.info("Newly generated:      %d", self.total_generated)
        logger.info("Skipped (existing):   %d", self.skipped_cached)
        if self.failed_generations:
            logger.error("Failed:               %d", len(self.failed_generations))
            logger.error("Failed prompts: %s", ', '.join(self.failed_generations))
        else:
            logger.info("Failed:               0")
        logger.info("=" * 70)


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)-8s %(message)s",
    )

    parser = argparse.ArgumentParser(
        description="Generate code using AI models (Ollama, OpenAI, or Claude)",
        epilog="""
Examples:
  # Use latest OpenAI models with caching
  python3 code_generator.py --model gpt-4o
  python3 code_generator.py --model chatgpt-4o-latest

  # Use latest Claude models (direct Anthropic API by default)
  python3 code_generator.py --model claude-opus-4
  python3 code_generator.py --model claude-sonnet-4

  # Use Claude via AWS Bedrock (requires AWS credentials)
  python3 code_generator.py --model claude-opus-4 --use-bedrock

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
    parser.add_argument(
        '--retries',
        type=int,
        default=3,
        help='Number of times to retry failed prompts (default: 3)'
    )
    parser.add_argument(
        '--use-bedrock',
        action='store_true',
        help='Use AWS Bedrock for Claude models instead of direct Anthropic API (requires AWS credentials)'
    )

    args = parser.parse_args()

    # Environment variable checks
    if any(x in args.model.lower() for x in ['gpt', 'chatgpt', 'o1', 'o3']) and not os.getenv('OPENAI_API_KEY'):
        logger.error("OPENAI_API_KEY environment variable not set")
        logger.error("Set it with: export OPENAI_API_KEY='your-key-here'")
        return 1

    if 'claude' in args.model.lower():
        if not args.use_bedrock and not (os.getenv('ANTHROPIC_API_KEY') or os.getenv('MYANTHROPIC_API_KEY')):
            logger.error("ANTHROPIC_API_KEY (or MYANTHROPIC_API_KEY) environment variable not set")
            logger.error("Set it with: export ANTHROPIC_API_KEY='your-key-here'")
            logger.error("Or: export MYANTHROPIC_API_KEY='your-key-here'")
            logger.error("Or: use --use-bedrock flag to use AWS Bedrock with AWS credentials")
            return 1

    if 'gemini' in args.model.lower() and not os.getenv('GEMINI_API_KEY'):
        logger.error("GEMINI_API_KEY environment variable not set")
        logger.error("Set it with: export GEMINI_API_KEY='your-key-here'")
        return 1

    try:
        generator = CodeGenerator(
            model=args.model,
            temperature=args.temperature,
            use_cache=not args.no_cache,
            force_regenerate=args.force_regenerate,
            timeout=args.timeout,
            use_bedrock=args.use_bedrock
        )
        generator.generate_from_prompts(
            args.prompts,
            args.output,
            limit=args.limit,
            retries=args.retries
        )
        return 0
    except Exception as e:
        logger.error("Fatal error: %s", e, exc_info=True)
        return 1


if __name__ == "__main__":
    exit(main())
