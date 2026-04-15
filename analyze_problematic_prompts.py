#!/usr/bin/env python3
"""
Identify prompts that multiple models are failing on.

This script analyzes benchmark reports across multiple models to identify
prompts that many/all models are refusing or failing to generate, which
may indicate problems with the prompt itself.
"""
import argparse
import json
from pathlib import Path
from typing import Dict, List
from collections import defaultdict


class ProblematicPromptAnalyzer:
    """Analyzes prompts that multiple models fail on."""

    def __init__(self):
        self.prompt_failures = defaultdict(lambda: {
            'models_failed': [],
            'models_succeeded': [],
            'failure_reasons': defaultdict(int),
            'prompt_info': {}
        })
        self.models_analyzed = set()

    def analyze_model_report(self, model_name: str, report_path: str):
        """Analyze a single model's benchmark report."""
        with open(report_path, 'r') as f:
            report = json.load(f)

        self.models_analyzed.add(model_name)

        # Track all prompts in this report
        prompts_in_report = set()

        # Analyze detailed results
        for result in report.get('detailed_results', []):
            prompt_id = result['prompt_id']
            prompts_in_report.add(prompt_id)

            # Store prompt info (category, language, etc.)
            if not self.prompt_failures[prompt_id]['prompt_info']:
                self.prompt_failures[prompt_id]['prompt_info'] = {
                    'category': result['category'],
                    'language': result['language'],
                    'prompt': result.get('prompt', '')[:100] + '...'  # First 100 chars
                }

            # Check if test was refused/unsupported
            vulns = result.get('vulnerabilities', [])
            is_refused = False
            reason = None

            for v in vulns:
                if isinstance(v, dict):
                    vtype = v.get('type', '')
                    desc = v.get('description', '')
                    if vtype == 'UNSUPPORTED' or 'UNSUPPORTED' in desc:
                        is_refused = True
                        reason = 'UNSUPPORTED'
                    if 'Unsupported language' in desc:
                        reason = 'Unsupported language'
                elif isinstance(v, str):
                    if 'Unsupported language' in v or 'UNSUPPORTED' in v:
                        is_refused = True
                        reason = 'Unsupported language'

            if is_refused:
                self.prompt_failures[prompt_id]['models_failed'].append(model_name)
                if reason:
                    self.prompt_failures[prompt_id]['failure_reasons'][reason] += 1
            else:
                self.prompt_failures[prompt_id]['models_succeeded'].append(model_name)

        # Analyze failed generations
        for failed in report.get('failed_generations', []):
            prompt_id = failed['prompt_id']
            prompts_in_report.add(prompt_id)

            # Store prompt info
            if not self.prompt_failures[prompt_id]['prompt_info']:
                self.prompt_failures[prompt_id]['prompt_info'] = {
                    'category': failed['category'],
                    'language': failed['language'],
                    'prompt': failed.get('prompt', '')[:100] + '...'
                }

            reason = failed.get('reason', 'Unknown')
            self.prompt_failures[prompt_id]['models_failed'].append(model_name)
            self.prompt_failures[prompt_id]['failure_reasons'][reason] += 1

    def generate_report(self, output_file: str = None, min_models_failed: int = 2):
        """
        Generate a report of problematic prompts.

        Args:
            output_file: Path to save report (None = print only)
            min_models_failed: Minimum number of models that must fail for a prompt to be included
        """
        report_lines = []
        report_lines.append("=" * 100)
        report_lines.append("PROBLEMATIC PROMPTS ANALYSIS")
        report_lines.append("=" * 100)
        report_lines.append(f"Models analyzed: {len(self.models_analyzed)}")
        report_lines.append(f"Models: {', '.join(sorted(self.models_analyzed))}")
        report_lines.append("")

        # Filter prompts that failed on multiple models
        problematic_prompts = {
            prompt_id: data
            for prompt_id, data in self.prompt_failures.items()
            if len(data['models_failed']) >= min_models_failed
        }

        report_lines.append(f"Prompts that failed on {min_models_failed}+ models: {len(problematic_prompts)}")
        report_lines.append("")

        # Sort by number of failures (descending)
        sorted_prompts = sorted(
            problematic_prompts.items(),
            key=lambda x: len(x[1]['models_failed']),
            reverse=True
        )

        # Group by failure rate
        failure_groups = {
            'all_models': [],
            'most_models': [],  # >75%
            'many_models': [],  # >50%
            'some_models': []   # >=min_models_failed
        }

        total_models = len(self.models_analyzed)
        for prompt_id, data in sorted_prompts:
            fail_count = len(data['models_failed'])
            fail_rate = fail_count / total_models

            if fail_count == total_models:
                failure_groups['all_models'].append((prompt_id, data))
            elif fail_rate > 0.75:
                failure_groups['most_models'].append((prompt_id, data))
            elif fail_rate > 0.5:
                failure_groups['many_models'].append((prompt_id, data))
            else:
                failure_groups['some_models'].append((prompt_id, data))

        # Report each group
        for group_name, group_prompts in failure_groups.items():
            if not group_prompts:
                continue

            group_titles = {
                'all_models': f'CRITICAL: Failed on ALL {total_models} models (likely prompt issue)',
                'most_models': f'HIGH: Failed on >75% of models ({len(group_prompts)} prompts)',
                'many_models': f'MEDIUM: Failed on >50% of models ({len(group_prompts)} prompts)',
                'some_models': f'LOW: Failed on {min_models_failed}+ models ({len(group_prompts)} prompts)'
            }

            report_lines.append("-" * 100)
            report_lines.append(group_titles[group_name])
            report_lines.append("-" * 100)

            for prompt_id, data in group_prompts:
                info = data['prompt_info']
                fail_count = len(data['models_failed'])
                success_count = len(data['models_succeeded'])
                fail_rate = fail_count / total_models * 100

                report_lines.append(f"\nPrompt: {prompt_id}")
                report_lines.append(f"  Category: {info['category']}")
                report_lines.append(f"  Language: {info['language']}")
                report_lines.append(f"  Failure rate: {fail_count}/{total_models} models ({fail_rate:.1f}%)")
                report_lines.append(f"  Failed on: {', '.join(sorted(data['models_failed']))}")
                if success_count > 0:
                    report_lines.append(f"  Succeeded on: {', '.join(sorted(data['models_succeeded']))}")

                # Show failure reasons
                if data['failure_reasons']:
                    report_lines.append(f"  Failure reasons:")
                    for reason, count in sorted(data['failure_reasons'].items(), key=lambda x: -x[1]):
                        report_lines.append(f"    - {reason}: {count} model(s)")

                # Show first 100 chars of prompt
                if info.get('prompt'):
                    report_lines.append(f"  Prompt text: {info['prompt']}")

        # Summary statistics
        report_lines.append("")
        report_lines.append("=" * 100)
        report_lines.append("SUMMARY STATISTICS")
        report_lines.append("=" * 100)
        report_lines.append(f"Total prompts analyzed: {len(self.prompt_failures)}")
        report_lines.append(f"Prompts that failed on ALL models: {len(failure_groups['all_models'])} (CRITICAL - likely prompt issues)")
        report_lines.append(f"Prompts that failed on >75% models: {len(failure_groups['most_models'])}")
        report_lines.append(f"Prompts that failed on >50% models: {len(failure_groups['many_models'])}")
        report_lines.append(f"Prompts that failed on {min_models_failed}+ models: {len(problematic_prompts)}")

        # Category breakdown for prompts that failed on all models
        if failure_groups['all_models']:
            report_lines.append("")
            report_lines.append("Categories of prompts that failed on ALL models:")
            cat_counts = defaultdict(int)
            for prompt_id, data in failure_groups['all_models']:
                cat = data['prompt_info']['category']
                cat_counts[cat] += 1

            for cat, count in sorted(cat_counts.items(), key=lambda x: -x[1]):
                report_lines.append(f"  {cat}: {count}")

        report_lines.append("")
        report_lines.append("=" * 100)

        report_text = '\n'.join(report_lines)

        # Print to console
        print(report_text)

        # Save to file if specified
        if output_file:
            Path(output_file).parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, 'w') as f:
                f.write(report_text)
            print(f"\nReport saved to: {output_file}")

        return report_text

    def generate_json_report(self, output_file: str):
        """Generate a JSON report for programmatic analysis."""
        json_report = {
            'models_analyzed': list(self.models_analyzed),
            'total_models': len(self.models_analyzed),
            'prompts': {}
        }

        for prompt_id, data in self.prompt_failures.items():
            json_report['prompts'][prompt_id] = {
                'models_failed': data['models_failed'],
                'models_succeeded': data['models_succeeded'],
                'failure_count': len(data['models_failed']),
                'success_count': len(data['models_succeeded']),
                'failure_rate': len(data['models_failed']) / len(self.models_analyzed) if self.models_analyzed else 0,
                'failure_reasons': dict(data['failure_reasons']),
                'info': data['prompt_info']
            }

        Path(output_file).parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w') as f:
            json.dump(json_report, f, indent=2)

        print(f"JSON report saved to: {output_file}")


def find_benchmark_reports(base_dir: str = 'output') -> Dict[str, str]:
    """Find all benchmark reports in output directories."""
    reports = {}
    base_path = Path(base_dir)

    # Find reports in output/model_name/ directories
    for model_dir in base_path.iterdir():
        if not model_dir.is_dir():
            continue

        report_file = model_dir / 'reports' / 'benchmark_report.json'
        if report_file.exists():
            reports[model_dir.name] = str(report_file)

    # Also check top-level reports directory
    top_report = Path('reports/benchmark_report.json')
    if top_report.exists():
        # Try to infer model name from report
        try:
            with open(top_report, 'r') as f:
                data = json.load(f)
                model_name = data.get('model_name', 'unknown')
                reports[model_name] = str(top_report)
        except:
            pass

    return reports


def main():
    parser = argparse.ArgumentParser(
        description="Identify prompts that multiple models are failing on"
    )
    parser.add_argument(
        '--models',
        type=str,
        nargs='+',
        help='Model names to analyze (if not specified, finds all in output/)'
    )
    parser.add_argument(
        '--reports',
        type=str,
        nargs='+',
        help='Paths to benchmark reports (if not specified, auto-discovers)'
    )
    parser.add_argument(
        '--min-failures',
        type=int,
        default=2,
        help='Minimum number of models that must fail for a prompt to be included (default: 2)'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='reports/problematic_prompts.txt',
        help='Output file for text report'
    )
    parser.add_argument(
        '--json',
        type=str,
        default='reports/problematic_prompts.json',
        help='Output file for JSON report'
    )

    args = parser.parse_args()

    analyzer = ProblematicPromptAnalyzer()

    # Discover reports if not specified
    if args.reports:
        # Use specified reports
        for i, report_path in enumerate(args.reports):
            model_name = args.models[i] if args.models and i < len(args.models) else f'model_{i+1}'
            analyzer.analyze_model_report(model_name, report_path)
    else:
        # Auto-discover
        reports = find_benchmark_reports()
        if not reports:
            print("No benchmark reports found. Run benchmarks first or specify --reports")
            return

        print(f"Found {len(reports)} model reports")
        for model_name, report_path in reports.items():
            print(f"  - {model_name}: {report_path}")
        print()

        for model_name, report_path in reports.items():
            analyzer.analyze_model_report(model_name, report_path)

    # Generate reports
    analyzer.generate_report(args.output, args.min_failures)

    if args.json:
        analyzer.generate_json_report(args.json)


if __name__ == '__main__':
    main()
