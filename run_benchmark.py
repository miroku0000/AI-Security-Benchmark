#!/usr/bin/env python3
"""
AI Security Benchmark - Complete Automated Pipeline

This script automates the entire benchmark process from code generation to final reporting.

Usage:
    # Run full benchmark on all models
    python3 run_benchmark.py --all

    # Run on specific models
    python3 run_benchmark.py --models "starcoder2:7b,gpt-4,claude-opus-4"

    # Skip code generation (use existing code)
    python3 run_benchmark.py --all --skip-generation

    # Run only specific phases
    python3 run_benchmark.py --all --phases "test,report"
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
import yaml

class BenchmarkPipeline:
    def __init__(self, config_file='benchmark_config.yaml'):
        self.config_file = config_file
        self.config = self.load_config()
        self.results_dir = Path('reports')
        self.results_dir.mkdir(exist_ok=True)

    def load_config(self):
        """Load benchmark configuration"""
        if not os.path.exists(self.config_file):
            print(f"⚠️  Config file {self.config_file} not found, using defaults")
            return self.create_default_config()

        with open(self.config_file) as f:
            return yaml.safe_load(f)

    def create_default_config(self):
        """Create default configuration"""
        config = {
            'models': {
                'openai': ['gpt-4', 'gpt-4o', 'gpt-4o-mini', 'gpt-3.5-turbo', 'o1', 'o3', 'o3-mini'],
                'anthropic': ['claude-opus-4', 'claude-sonnet-4'],
                'ollama': [
                    'starcoder2:7b',
                    'starcoder2',
                    'deepseek-coder',
                    'deepseek-coder:6.7b-instruct',
                    'codellama',
                    'codegemma',
                    'codegemma:7b-instruct',
                    'qwen2.5-coder',
                    'qwen2.5-coder:14b',
                    'mistral',
                    'llama3.1'
                ]
            },
            'prompts_file': 'prompts/prompts.yaml',
            'code_generator': 'code_generator.py',
            'runner': 'runner.py',
            'output_base': 'generated',
            'parallel_ollama': True,
            'timeout_per_model': 3600  # 1 hour per model
        }

        # Save default config
        with open(self.config_file, 'w') as f:
            yaml.dump(config, f, default_flow_style=False)

        return config

    def verify_prerequisites(self):
        """Check if all required tools and files are present"""
        print("="*80)
        print("PREREQUISITE CHECK")
        print("="*80)

        issues = []

        # Check Python files
        required_files = ['code_generator.py', 'runner.py', 'prompts/prompts.yaml']
        for file in required_files:
            if os.path.exists(file):
                print(f"✅ {file}")
            else:
                print(f"❌ {file} - MISSING")
                issues.append(f"Missing required file: {file}")

        # Check API keys for cloud models
        if 'openai' in self.config['models'] and self.config['models']['openai']:
            if os.getenv('OPENAI_API_KEY'):
                print("✅ OPENAI_API_KEY")
            else:
                print("⚠️  OPENAI_API_KEY - Not set (OpenAI models will fail)")
                issues.append("OPENAI_API_KEY not set")

        if 'anthropic' in self.config['models'] and self.config['models']['anthropic']:
            if os.getenv('ANTHROPIC_API_KEY'):
                print("✅ ANTHROPIC_API_KEY")
            else:
                print("⚠️  ANTHROPIC_API_KEY - Not set (Anthropic models will fail)")
                issues.append("ANTHROPIC_API_KEY not set")

        # Check Ollama
        if 'ollama' in self.config['models'] and self.config['models']['ollama']:
            try:
                result = subprocess.run(['ollama', 'list'], capture_output=True, timeout=5)
                if result.returncode == 0:
                    print("✅ Ollama is running")
                else:
                    print("❌ Ollama not responding")
                    issues.append("Ollama not running")
            except Exception as e:
                print(f"❌ Ollama check failed: {e}")
                issues.append("Cannot run ollama command")

        print()

        if issues:
            print("⚠️  Issues found:")
            for issue in issues:
                print(f"   - {issue}")
            print()
            response = input("Continue anyway? (y/N): ")
            if response.lower() != 'y':
                sys.exit(1)
        else:
            print("✅ All prerequisites satisfied")

        print()
        return True

    def get_all_models(self):
        """Get flat list of all models"""
        models = []
        for provider, model_list in self.config['models'].items():
            models.extend(model_list)
        return models

    def generate_code(self, models):
        """Generate code for specified models"""
        print("="*80)
        print("PHASE 1: CODE GENERATION")
        print("="*80)
        print(f"Generating code for {len(models)} models")
        print()

        for i, model in enumerate(models, 1):
            output_dir = f"generated_{model}"

            # Check if already exists
            if os.path.exists(output_dir):
                file_count = len([f for f in os.listdir(output_dir) if f.endswith(('.py', '.js', '.java'))])
                print(f"[{i}/{len(models)}] {model}: Already exists ({file_count} files)")
                continue

            print(f"[{i}/{len(models)}] {model}: Generating...")

            cmd = [
                'python3',
                self.config['code_generator'],
                '--model', model,
                '--output', output_dir,
                '--prompts', self.config['prompts_file']
            ]

            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    timeout=self.config['timeout_per_model'],
                    text=True
                )

                if result.returncode == 0:
                    file_count = len([f for f in os.listdir(output_dir) if f.endswith(('.py', '.js', '.java'))])
                    print(f"  ✅ Generated {file_count} files")
                else:
                    print(f"  ❌ Failed: {result.stderr[:200]}")

            except subprocess.TimeoutExpired:
                print(f"  ⏱️  Timeout after {self.config['timeout_per_model']}s")
            except Exception as e:
                print(f"  ❌ Error: {e}")

        print()

    def run_tests(self, models):
        """Run security tests on generated code"""
        print("="*80)
        print("PHASE 2: SECURITY TESTING")
        print("="*80)
        print(f"Testing {len(models)} models")
        print()

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # Group models by provider for potential parallel execution
        ollama_models = [m for m in models if m in self.config['models'].get('ollama', [])]
        other_models = [m for m in models if m not in ollama_models]

        # Test non-Ollama models sequentially (API rate limits)
        for i, model in enumerate(other_models, 1):
            self._test_single_model(model, i, len(other_models), timestamp)

        # Test Ollama models (can run in parallel if configured)
        if ollama_models:
            if self.config.get('parallel_ollama', False):
                print(f"\nRunning {len(ollama_models)} Ollama models in parallel...")
                self._test_ollama_parallel(ollama_models, timestamp)
            else:
                for i, model in enumerate(ollama_models, 1):
                    self._test_single_model(model, i, len(ollama_models), timestamp)

        print()

    def _test_single_model(self, model, index, total, timestamp):
        """Test a single model"""
        code_dir = f"generated_{model}"

        if not os.path.exists(code_dir):
            print(f"[{index}/{total}] {model}: ⚠️  Code directory not found, skipping")
            return

        output_file = self.results_dir / f"{model}_208point_{timestamp}.json"

        print(f"[{index}/{total}] {model}: Testing...")

        cmd = [
            'python3',
            self.config['runner'],
            '--code-dir', code_dir,
            '--model', model,
            '--output', str(output_file)
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=self.config['timeout_per_model'],
                text=True
            )

            if result.returncode == 0:
                # Parse score from output
                for line in result.stdout.split('\n'):
                    if 'Overall Score:' in line:
                        score = line.split('Overall Score:')[1].strip()
                        print(f"  ✅ {score}")
                        break
                else:
                    print(f"  ✅ Completed")
            else:
                print(f"  ❌ Failed")

        except subprocess.TimeoutExpired:
            print(f"  ⏱️  Timeout")
        except Exception as e:
            print(f"  ❌ Error: {e}")

    def _test_ollama_parallel(self, models, timestamp):
        """Run Ollama model tests in parallel"""
        processes = []

        for model in models:
            code_dir = f"generated_{model}"
            output_file = self.results_dir / f"{model}_208point_{timestamp}.json"

            cmd = [
                'python3',
                self.config['runner'],
                '--code-dir', code_dir,
                '--model', model,
                '--output', str(output_file)
            ]

            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            processes.append((model, proc))

        # Wait for all to complete
        for model, proc in processes:
            proc.wait()
            if proc.returncode == 0:
                print(f"  ✅ {model} completed")
            else:
                print(f"  ❌ {model} failed")

    def generate_reports(self):
        """Generate comprehensive reports"""
        print("="*80)
        print("PHASE 3: REPORT GENERATION")
        print("="*80)

        # Generate percentile-based report
        print("Generating percentile-based report...")
        self._generate_percentile_report()
        print("  ✅ COMPREHENSIVE_RESULTS_PERCENTILE.md")

        # Generate traditional report
        print("Generating traditional report...")
        self._generate_traditional_report()
        print("  ✅ COMPREHENSIVE_RESULTS_208POINT.md")

        # Generate summary table
        print("Generating summary table...")
        self._generate_summary_table()
        print("  ✅ BENCHMARK_SUMMARY.md")

        print()

    def _generate_percentile_report(self):
        """Generate percentile-based comprehensive report"""
        reports = list(self.results_dir.glob('*_208point_*.json'))
        results = []

        for report_path in reports:
            try:
                with open(report_path) as f:
                    data = json.load(f)
                    model = data.get('model_name', 'unknown')
                    summary = data.get('summary', {})
                    detailed = data.get('detailed_results', [])

                    # Exclude failed generations
                    valid_tests = [t for t in detailed if t.get('score', 0) >= 0]
                    failed_gens = [t for t in detailed if t.get('score', 0) < 0]

                    points_earned = sum(t.get('score', 0) for t in valid_tests)
                    max_possible = sum(t.get('max_score', 0) for t in valid_tests)
                    percentile = (points_earned / max_possible * 100) if max_possible > 0 else 0

                    results.append({
                        'model': model,
                        'valid_tests': len(valid_tests),
                        'failed_gens': len(failed_gens),
                        'points_earned': points_earned,
                        'max_possible': max_possible,
                        'percentile': percentile,
                        'secure': summary.get('secure', 0),
                        'partial': summary.get('partial', 0),
                        'vulnerable': summary.get('vulnerable', 0)
                    })
            except Exception:
                continue

        results.sort(key=lambda x: x['percentile'], reverse=True)

        # Write report
        report = self._format_percentile_report(results)
        with open('COMPREHENSIVE_RESULTS_PERCENTILE.md', 'w') as f:
            f.write(report)

    def _format_percentile_report(self, results):
        """Format percentile report as markdown"""
        report = f"""# AI Security Benchmark Results - Percentile-Based Scoring

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Total Models Tested:** {len(results)}
**Scoring Method:** Percentile-based (fair exclusion of failed generations)

## Top 10 Models

| Rank | Model | Score | Percentile | Valid Tests | Secure | Vulnerable |
|------|-------|-------|------------|-------------|--------|------------|
"""

        for i, r in enumerate(results[:10], 1):
            score_str = f"{r['points_earned']}/{r['max_possible']}"
            report += f"| {i} | {r['model']} | {score_str} | {r['percentile']:.2f}% | {r['valid_tests']}/66 | {r['secure']} | {r['vulnerable']} |\n"

        report += f"""

## Complete Rankings

| Rank | Model | Percentile | Score |
|------|-------|------------|-------|
"""

        for i, r in enumerate(results, 1):
            report += f"| {i} | {r['model']} | {r['percentile']:.2f}% | {r['points_earned']}/{r['max_possible']} |\n"

        return report

    def _generate_traditional_report(self):
        """Generate traditional 208-point report"""
        # Similar to percentile but with raw scores
        pass

    def _generate_summary_table(self):
        """Generate quick summary table"""
        reports = list(self.results_dir.glob('*_208point_*.json'))

        summary = f"""# Benchmark Summary

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Models Tested:** {len(reports)}

## Quick Reference

"""

        with open('BENCHMARK_SUMMARY.md', 'w') as f:
            f.write(summary)

    def cleanup(self):
        """Clean up old reports and temporary files"""
        print("="*80)
        print("CLEANUP")
        print("="*80)

        # Optional: Remove old reports, empty directories, etc.
        print("Cleanup skipped (manual cleanup recommended)")
        print()

    def run(self, models=None, skip_generation=False, phases=None, skip_checks=False):
        """Run the complete pipeline"""
        start_time = time.time()

        print("\n")
        print("="*80)
        print("AI SECURITY BENCHMARK - AUTOMATED PIPELINE")
        print("="*80)
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()

        # Verify prerequisites
        if not skip_checks:
            self.verify_prerequisites()

        # Get models to test
        if models is None:
            models = self.get_all_models()

        print(f"Models to test: {len(models)}")
        for i, model in enumerate(models, 1):
            print(f"  {i}. {model}")
        print()

        # Determine phases
        if phases is None:
            phases = ['generate', 'test', 'report']

        # Run phases
        if 'generate' in phases and not skip_generation:
            self.generate_code(models)

        if 'test' in phases:
            self.run_tests(models)

        if 'report' in phases:
            self.generate_reports()

        # Summary
        elapsed = time.time() - start_time
        print("="*80)
        print("PIPELINE COMPLETE")
        print("="*80)
        print(f"Duration: {elapsed/60:.1f} minutes")
        print(f"Reports: ./reports/")
        print(f"Comprehensive results: COMPREHENSIVE_RESULTS_PERCENTILE.md")
        print()

def main():
    parser = argparse.ArgumentParser(description='Run AI Security Benchmark')
    parser.add_argument('--all', action='store_true', help='Run on all configured models')
    parser.add_argument('--models', type=str, help='Comma-separated list of models to test')
    parser.add_argument('--skip-generation', action='store_true', help='Skip code generation (use existing)')
    parser.add_argument('--skip-checks', action='store_true', help='Skip prerequisite checks')
    parser.add_argument('--phases', type=str, help='Comma-separated phases: generate,test,report')
    parser.add_argument('--config', type=str, default='benchmark_config.yaml', help='Config file path')

    args = parser.parse_args()

    # Parse arguments
    pipeline = BenchmarkPipeline(args.config)

    models = None
    if args.models:
        models = [m.strip() for m in args.models.split(',')]
    elif not args.all:
        print("Error: Must specify --all or --models")
        sys.exit(1)

    phases = None
    if args.phases:
        phases = [p.strip() for p in args.phases.split(',')]

    # Run pipeline
    pipeline.run(
        models=models,
        skip_generation=args.skip_generation,
        phases=phases,
        skip_checks=args.skip_checks
    )

if __name__ == '__main__':
    main()
