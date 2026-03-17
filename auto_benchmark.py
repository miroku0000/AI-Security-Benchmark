#!/usr/bin/env python3
"""
Automated Security Benchmark

Automatically generates code using AI models (Ollama, OpenAI, or Claude) and runs security tests.
This is the main entry point for end-to-end automated testing.
"""
import argparse
import subprocess
import sys
import json
from pathlib import Path
from datetime import datetime


class AutomatedBenchmark:
    """Automated code generation and security testing."""

    def __init__(self, model: str, output_dir: str, report_name: str = None,
                 use_cache: bool = True, force_regenerate: bool = False):
        self.model = model
        self.output_dir = output_dir
        self.report_name = report_name or f"{model.replace(':', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.use_cache = use_cache
        self.force_regenerate = force_regenerate

    def run_generation(self, limit: int = None) -> bool:
        """Run code generation step."""
        print(f"\n{'='*70}")
        print("STEP 1: CODE GENERATION")
        print(f"{'='*70}\n")

        cmd = [
            'python3', 'code_generator.py',
            '--model', self.model,
            '--output', self.output_dir,
        ]

        if limit:
            cmd.extend(['--limit', str(limit)])

        # Add cache flags
        if not self.use_cache:
            cmd.append('--no-cache')
        if self.force_regenerate:
            cmd.append('--force-regenerate')

        try:
            result = subprocess.run(cmd, timeout=600)
            return result.returncode == 0
        except subprocess.TimeoutExpired:
            print("Error: Code generation timed out")
            return False
        except Exception as e:
            print(f"Error running generation: {e}")
            return False

    def run_benchmark(self, html: bool = True) -> bool:
        """Run security benchmark on generated code."""
        print(f"\n{'='*70}")
        print("STEP 2: SECURITY TESTING")
        print(f"{'='*70}\n")

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
                # Load and display summary
                self._display_summary(report_path)
                return True
            return False
        except Exception as e:
            print(f"Error running benchmark: {e}")
            return False

    def _display_summary(self, report_path: str):
        """Display benchmark summary."""
        try:
            with open(report_path, 'r') as f:
                report = json.load(f)

            summary = report.get('summary', {})

            print(f"\n{'='*70}")
            print("FINAL RESULTS")
            print(f"{'='*70}")
            print(f"Model: {self.model}")
            print(f"Total Tests: {summary.get('total_tests', 0)}")
            print(f"✅ Secure: {summary.get('secure', 0)}")
            print(f"⚠️  Partial: {summary.get('partial', 0)}")
            print(f"❌ Vulnerable: {summary.get('vulnerable', 0)}")
            print(f"\nOverall Score: {summary.get('overall_score', 'N/A')}")
            print(f"Percentage: {summary.get('percentage', 0):.1f}%")
            print(f"\nJSON Report: {report_path}")

            # Check for HTML report
            html_path = report_path.replace('.json', '.html')
            if Path(html_path).exists():
                print(f"HTML Report: {html_path}")
                print(f"\nOpen in browser: file://{Path(html_path).absolute()}")

            print(f"{'='*70}\n")

        except Exception as e:
            print(f"Error displaying summary: {e}")

    def run(self, limit: int = None) -> int:
        """Run the full automated benchmark."""
        print(f"\n{'='*70}")
        print("AUTOMATED AI SECURITY BENCHMARK")
        print(f"{'='*70}")
        print(f"Model: {self.model}")
        print(f"Output Directory: {self.output_dir}")
        print(f"Report Name: {self.report_name}")
        print(f"{'='*70}\n")

        # Step 1: Generate code
        if not self.run_generation(limit):
            print("❌ Code generation failed")
            return 1

        # Step 2: Run security tests
        if not self.run_benchmark():
            print("❌ Security testing failed")
            return 1

        print("\n✅ Automated benchmark completed successfully!\n")
        return 0


def main():
    parser = argparse.ArgumentParser(
        description="Automated AI code security benchmark using Ollama, OpenAI, or Claude",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test with Ollama models
  python3 auto_benchmark.py --model codellama
  python3 auto_benchmark.py --model deepseek-coder

  # Test with latest OpenAI models (requires OPENAI_API_KEY)
  export OPENAI_API_KEY='your-key-here'
  python3 auto_benchmark.py --model gpt-4o
  python3 auto_benchmark.py --model chatgpt-4o-latest

  # Test with latest Claude models (requires ANTHROPIC_API_KEY)
  export ANTHROPIC_API_KEY='your-key-here'
  python3 auto_benchmark.py --model claude-opus-4
  python3 auto_benchmark.py --model claude-sonnet-4

  # Quick test with only 5 prompts
  python3 auto_benchmark.py --model gpt-4o --limit 5

  # Caching examples (by default, caching is enabled)
  python3 auto_benchmark.py --model gpt-4o  # Uses cache, skips unchanged prompts
  python3 auto_benchmark.py --model gpt-4o --force-regenerate  # Regenerate all, update cache
  python3 auto_benchmark.py --model gpt-4o --no-cache  # Disable caching entirely

  # Compare multiple models (cache makes this faster)
  python3 auto_benchmark.py --model codellama
  python3 auto_benchmark.py --model gpt-4o
  python3 auto_benchmark.py --model claude-opus-4
        """
    )

    parser.add_argument(
        '--model',
        type=str,
        default='codellama',
        help='Model to use: Ollama (codellama, deepseek-coder, starcoder2), OpenAI (gpt-4o, chatgpt-4o-latest, o1, o3), or Claude (claude-opus-4, claude-sonnet-4)'
    )
    parser.add_argument(
        '--output',
        type=str,
        default=None,
        help='Output directory for generated code (default: generated_<model>)'
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

    # Determine output directory
    output_dir = args.output or f"generated_{args.model.replace(':', '_')}"

    # Create benchmark instance
    benchmark = AutomatedBenchmark(
        model=args.model,
        output_dir=output_dir,
        report_name=args.report_name,
        use_cache=not args.no_cache,
        force_regenerate=args.force_regenerate
    )

    # Run automated benchmark
    return benchmark.run(limit=args.limit)


if __name__ == "__main__":
    sys.exit(main())
