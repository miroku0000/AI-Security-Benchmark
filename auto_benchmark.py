#!/usr/bin/env python3
"""
Automated Security Benchmark

Automatically generates code using AI models (Ollama, OpenAI, or Claude) and runs security tests.
This is the main entry point for end-to-end automated testing.

Usage:
  python3 auto_benchmark.py --all --retries 3          # Run ALL models from config
  python3 auto_benchmark.py --model codellama --retries 3  # Run a single model
  python3 auto_benchmark.py --all --limit 5            # Quick test (5 prompts)
"""
import argparse
import logging
import os
import subprocess
import sys
import json
import yaml
import concurrent.futures
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


class AutomatedBenchmark:
    """Automated code generation and security testing."""

    def __init__(self, model: str, output_dir: str, report_name: str = None,
                 use_cache: bool = True, force_regenerate: bool = False,
                 retries: int = 0):
        self.model = model
        self.output_dir = output_dir
        self.report_name = report_name or f"{model.replace(':', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.use_cache = use_cache
        self.force_regenerate = force_regenerate
        self.retries = retries

    def run_generation(self, limit: int = None) -> bool:
        """Run code generation step."""
        logger.info("=" * 70)
        logger.info("STEP 1: CODE GENERATION")
        logger.info("=" * 70)

        cmd = [
            'python3', 'code_generator.py',
            '--model', self.model,
            '--output', self.output_dir,
        ]

        if limit:
            cmd.extend(['--limit', str(limit)])
        if self.retries > 0:
            cmd.extend(['--retries', str(self.retries)])
        if not self.use_cache:
            cmd.append('--no-cache')
        if self.force_regenerate:
            cmd.append('--force-regenerate')

        try:
            result = subprocess.run(cmd)
            return result.returncode == 0
        except Exception as e:
            logger.error("Error running generation: %s", e)
            return False

    def run_benchmark(self, html: bool = True) -> dict:
        """Run security benchmark on generated code. Returns summary dict or None."""
        logger.info("=" * 70)
        logger.info("STEP 2: SECURITY TESTING")
        logger.info("=" * 70)

        report_path = f"reports/{self.report_name}.json"

        cmd = [
            'python3', 'runner.py',
            '--code-dir', self.output_dir,
            '--output', report_path,
            '--model', self.model
        ]

        if not html:
            cmd.append('--no-html')

        try:
            result = subprocess.run(cmd)

            if result.returncode == 0:
                summary = self._display_summary(report_path)
                return summary
            return None
        except Exception as e:
            logger.error("Error running benchmark: %s", e)
            return None

    def _display_summary(self, report_path: str) -> dict:
        """Display benchmark summary. Returns summary dict."""
        try:
            with open(report_path, 'r') as f:
                report = json.load(f)

            summary = report.get('summary', {})

            logger.info("=" * 70)
            logger.info("FINAL RESULTS")
            logger.info("=" * 70)
            logger.info("Model: %s", self.model)
            logger.info("Total Tests: %s", summary.get('total_tests', 0))
            logger.info("Secure: %s", summary.get('secure', 0))
            logger.info("Partial: %s", summary.get('partial', 0))
            logger.info("Vulnerable: %s", summary.get('vulnerable', 0))
            logger.info("Overall Score: %s", summary.get('overall_score', 'N/A'))
            logger.info("Percentage: %.1f%%", summary.get('percentage', 0))
            logger.info("JSON Report: %s", report_path)

            html_path = report_path.replace('.json', '.html')
            if Path(html_path).exists():
                logger.info("HTML Report: %s", html_path)

            logger.info("=" * 70)
            return summary

        except Exception as e:
            logger.error("Error displaying summary: %s", e)
            return {}

    def _has_generated_code(self) -> bool:
        """Check if generated code directory exists and has files."""
        output_path = Path(self.output_dir)
        if not output_path.exists():
            return False
        code_files = list(output_path.glob('*.py')) + list(output_path.glob('*.js'))
        return len(code_files) > 0

    def run(self, limit: int = None) -> dict:
        """Run the full automated benchmark. Returns summary dict or None on failure."""
        start_time = datetime.now()
        logger.info("=" * 70)
        logger.info("AUTOMATED AI SECURITY BENCHMARK")
        logger.info("=" * 70)
        logger.info("Model: %s", self.model)
        logger.info("Output Directory: %s", self.output_dir)
        logger.info("Report Name: %s", self.report_name)
        logger.info("Started: %s", start_time.strftime('%Y-%m-%d %H:%M:%S'))
        logger.info("=" * 70)

        # Step 1: Generate code (skip if code already exists and no forced regeneration)
        if self._has_generated_code() and not self.force_regenerate and limit is None:
            logger.info("Using existing code in %s/ (use --force-regenerate to regenerate)", self.output_dir)
        elif not self.run_generation(limit):
            logger.error("Code generation failed")
            return None

        # Check file count — skip benchmarking if incomplete
        expected = limit or 66
        output_path = Path(self.output_dir)
        code_files = list(output_path.glob('*.py')) + list(output_path.glob('*.js')) if output_path.exists() else []
        file_count = len(code_files)
        if file_count < expected:
            logger.warning("%s: Only %d/%d files generated -- skipping benchmark", self.model, file_count, expected)
            logger.warning("Cannot compare against models with complete generation.")
            return None

        # Step 2: Run security tests
        summary = self.run_benchmark()
        if summary is None:
            logger.error("Security testing failed")
            return None

        elapsed = datetime.now() - start_time
        minutes = int(elapsed.total_seconds() // 60)
        seconds = int(elapsed.total_seconds() % 60)
        logger.info("Completed %s in %dm %ds", self.model, minutes, seconds)
        return summary


def _detect_provider(model: str) -> str:
    """Detect provider from model name."""
    model_lower = model.lower()
    if any(x in model_lower for x in ['gpt-3', 'gpt-4', 'gpt-5', 'o1', 'o3', 'o4', 'chatgpt']):
        return 'openai'
    if 'claude' in model_lower:
        return 'anthropic'
    if 'gemini' in model_lower:
        return 'google'
    return 'ollama'


def load_models_from_config(config_path: str = 'benchmark_config.yaml') -> dict:
    """Load model lists from config, grouped by provider."""
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    models_config = config.get('models', {})
    return {
        'openai': models_config.get('openai', []),
        'anthropic': models_config.get('anthropic', []),
        'google': models_config.get('google', []),
        'ollama': models_config.get('ollama', []),
    }


def run_all_models(args):
    """Run benchmark for all models in config."""
    models_by_provider = load_models_from_config()
    all_results = {}

    api_models = models_by_provider['openai'] + models_by_provider['anthropic'] + models_by_provider['google']
    ollama_models = models_by_provider['ollama']

    total = len(api_models) + len(ollama_models)
    run_start = datetime.now()
    logger.info("=" * 70)
    logger.info("FULL BENCHMARK: %d models", total)
    logger.info("=" * 70)
    logger.info("API models (parallel):      %d", len(api_models))
    logger.info("Ollama models (sequential): %d", len(ollama_models))
    logger.info("Started: %s", run_start.strftime('%Y-%m-%d %H:%M:%S'))
    logger.info("=" * 70)

    # Check API keys
    has_openai = bool(os.getenv('OPENAI_API_KEY'))
    has_anthropic = bool(os.getenv('ANTHROPIC_API_KEY'))

    if models_by_provider['openai'] and not has_openai:
        logger.warning("OPENAI_API_KEY not set, skipping OpenAI models")
        api_models = [m for m in api_models if _detect_provider(m) != 'openai']

    if models_by_provider['anthropic'] and not has_anthropic:
        logger.warning("ANTHROPIC_API_KEY not set, skipping Anthropic models")
        api_models = [m for m in api_models if _detect_provider(m) != 'anthropic']

    has_google = bool(os.getenv('GEMINI_API_KEY'))
    if models_by_provider['google'] and not has_google:
        logger.warning("GEMINI_API_KEY not set, skipping Google models")
        api_models = [m for m in api_models if _detect_provider(m) != 'google']

    def run_single_model(model):
        """Run benchmark for a single model. Returns (model, summary, files_generated)."""
        output_dir = f"output/{model.replace(':', '_')}"
        report_name = f"{model.replace(':', '_')}_208point_{datetime.now().strftime('%Y%m%d')}"
        benchmark = AutomatedBenchmark(
            model=model,
            output_dir=output_dir,
            report_name=report_name,
            use_cache=not args.no_cache,
            force_regenerate=args.force_regenerate,
            retries=args.retries,
        )
        summary = benchmark.run(limit=args.limit)
        # Count actual generated files
        out_path = Path(output_dir)
        files = list(out_path.glob('*.py')) + list(out_path.glob('*.js')) if out_path.exists() else []
        return model, summary, len(files)

    # Run API models in parallel
    if api_models:
        logger.info("=" * 70)
        logger.info("PHASE 1: API MODELS (%d models in parallel)", len(api_models))
        logger.info("=" * 70)

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = {executor.submit(run_single_model, m): m for m in api_models}
            for future in concurrent.futures.as_completed(futures):
                model, summary, files = future.result()
                all_results[model] = (summary, files)

    # Run Ollama models sequentially
    if ollama_models:
        logger.info("=" * 70)
        logger.info("PHASE 2: OLLAMA MODELS (%d models, sequential)", len(ollama_models))
        logger.info("=" * 70)

        for i, model in enumerate(ollama_models, 1):
            logger.info(">>> Ollama model %d/%d: %s", i, len(ollama_models), model)
            model_name, summary, files = run_single_model(model)
            all_results[model_name] = (summary, files)

    # Generate HTML reports
    logger.info("=" * 70)
    logger.info("PHASE 3: GENERATING HTML REPORTS")
    logger.info("=" * 70)

    subprocess.run(['python3', 'utils/generate_html_reports.py'])

    # Print final summary table
    logger.info("=" * 70)
    logger.info("FINAL RESULTS -- ALL MODELS")
    logger.info("=" * 70)
    logger.info("%-6s%-30s%-18s%-10s%-12s", "Rank", "Model", "Score", "Files", "Provider")
    logger.info("-" * 76)

    complete = []
    incomplete = []
    for model, (summary, files) in all_results.items():
        provider = _detect_provider(model)
        if summary is None:
            incomplete.append((model, files, provider))
        else:
            score = summary.get('overall_score', '0/208')
            pct = summary.get('percentage', 0)
            complete.append((model, score, pct, files, provider))

    complete.sort(key=lambda x: x[2], reverse=True)
    incomplete.sort(key=lambda x: x[1], reverse=True)

    rank = 1
    for model, score, pct, files, provider in complete:
        logger.info("%-6d%-30s%s (%.1f%%)   %d/66    %-12s", rank, model, score, pct, files, provider)
        rank += 1

    if incomplete:
        logger.warning("--- Incomplete generation (not ranked, not benchmarked) ---")
        for model, files, provider in incomplete:
            logger.warning("%-6s%-30s%-18s%d/66    %-12s", "--", model, "N/A", files, provider)

    logger.info("=" * 76)

    total_elapsed = datetime.now() - run_start
    total_min = int(total_elapsed.total_seconds() // 60)
    total_sec = int(total_elapsed.total_seconds() % 60)
    logger.info("Total time: %dm %ds", total_min, total_sec)
    logger.info("Finished: %s", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    logger.info("=" * 70)

    failed = [m for m, (s, _) in all_results.items() if s is None]
    if failed:
        return 1
    return 0


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)-8s %(message)s",
    )

    parser = argparse.ArgumentParser(
        description="Automated AI code security benchmark",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run ALL models from benchmark_config.yaml (recommended)
  python3 auto_benchmark.py --all --retries 3

  # Quick test (5 prompts only)
  python3 auto_benchmark.py --all --retries 3 --limit 5

  # Single model
  python3 auto_benchmark.py --model codellama --retries 3

  # Force regenerate everything
  python3 auto_benchmark.py --all --force-regenerate --retries 3
        """
    )

    parser.add_argument(
        '--all',
        action='store_true',
        help='Run all models from benchmark_config.yaml (API in parallel, Ollama sequential)'
    )
    parser.add_argument(
        '--model',
        type=str,
        default='codellama',
        help='Single model to test (ignored if --all is used)'
    )
    parser.add_argument(
        '--output',
        type=str,
        default=None,
        help='Output directory for generated code (default: output/<model>)'
    )
    parser.add_argument(
        '--report-name',
        type=str,
        help='Custom report name (default: <model>_<timestamp>)'
    )
    parser.add_argument(
        '--limit',
        type=int,
        help='Limit number of prompts (for quick testing)'
    )
    parser.add_argument(
        '--retries',
        type=int,
        default=3,
        help='Number of times to retry failed prompts (default: 3)'
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
    args = parser.parse_args()

    if args.all:
        return run_all_models(args)

    # Single model mode
    output_dir = args.output or f"output/{args.model.replace(':', '_')}"
    report_name = args.report_name or f"{args.model.replace(':', '_')}_208point_{datetime.now().strftime('%Y%m%d')}"

    benchmark = AutomatedBenchmark(
        model=args.model,
        output_dir=output_dir,
        report_name=report_name,
        use_cache=not args.no_cache,
        force_regenerate=args.force_regenerate,
        retries=args.retries,
    )

    summary = benchmark.run(limit=args.limit)
    return 0 if summary else 1


if __name__ == "__main__":
    sys.exit(main())
