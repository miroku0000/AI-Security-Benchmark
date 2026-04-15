#!/usr/bin/env python3
"""
Iterative Detector Refinement Framework

Performs systematic refinement of security detectors by:
1. Analyzing all models for false positives/negatives
2. Identifying patterns in detection failures
3. Generating improvement recommendations
4. Implementing improvements
5. Re-running analysis to measure convergence

Goal: Minimize false positives and false negatives across all models.
"""
import json
import sys
import subprocess
from pathlib import Path
from collections import defaultdict
from datetime import datetime

class IterativeRefinementFramework:
    def __init__(self, models_to_analyze=None, max_iterations=5):
        self.models_to_analyze = models_to_analyze or []
        self.max_iterations = max_iterations
        self.iteration = 0
        self.convergence_threshold = 0.02  # 2% improvement threshold
        self.results_dir = Path("reports/refinement")
        self.results_dir.mkdir(parents=True, exist_ok=True)

        # Track metrics across iterations
        self.iteration_metrics = []

    def run_analysis_for_model(self, model_name):
        """Run security analysis for a single model."""
        output_dir = f"output/{model_name}"
        report_path = f"reports/{model_name}_analysis.json"

        print(f"  Analyzing {model_name}...")

        cmd = [
            "python3", "runner.py",
            "--code-dir", output_dir,
            "--output", report_path,
            "--model", model_name
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            if result.returncode == 0:
                return report_path
            else:
                print(f"    ERROR: Analysis failed for {model_name}")
                print(f"    {result.stderr[:200]}")
                return None
        except subprocess.TimeoutExpired:
            print(f"    ERROR: Analysis timed out for {model_name}")
            return None
        except Exception as e:
            print(f"    ERROR: {e}")
            return None

    def run_false_analysis_for_model(self, model_name, report_path):
        """Run false positive/negative analysis for a model."""
        output_file = f"reports/refinement/{model_name}_false_analysis_iter{self.iteration}.md"

        cmd = [
            "python3", "analyze_false_results.py",
            model_name,
            report_path,
            "--output", output_file
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            if result.returncode == 0:
                # Parse output to extract statistics
                stats = self.parse_false_analysis_output(result.stdout)
                return stats
            else:
                print(f"    ERROR: False analysis failed for {model_name}")
                return None
        except Exception as e:
            print(f"    ERROR: {e}")
            return None

    def parse_false_analysis_output(self, output):
        """Parse false analysis output to extract key metrics."""
        stats = {
            'total_tests': 0,
            'passed': 0,
            'failed': 0,
            'false_positives': 0,
            'false_negatives': 0,
            'severity_passed': 0,
            'severity_failed': 0
        }

        for line in output.split('\n'):
            if 'Total Tests:' in line:
                stats['total_tests'] = int(line.split(':')[1].strip())
            elif 'Passed:' in line and 'Original' not in line and 'Severity' not in line:
                parts = line.split('(')
                if len(parts) > 0:
                    stats['passed'] = int(parts[0].split(':')[1].strip())
            elif 'Failed:' in line and 'Original' not in line and 'Severity' not in line:
                parts = line.split('(')
                if len(parts) > 0:
                    stats['failed'] = int(parts[0].split(':')[1].strip())
            elif 'False Positives:' in line:
                stats['false_positives'] = int(line.split(':')[1].strip())
            elif 'False Negatives:' in line:
                stats['false_negatives'] = int(line.split(':')[1].strip())

        return stats

    def aggregate_false_patterns(self, all_stats):
        """Aggregate false positive/negative patterns across all models."""
        aggregated = {
            'total_tests': sum(s['total_tests'] for s in all_stats.values()),
            'total_false_positives': sum(s['false_positives'] for s in all_stats.values()),
            'total_false_negatives': sum(s['false_negatives'] for s in all_stats.values()),
            'models_analyzed': len(all_stats),
            'avg_fp_rate': 0.0,
            'avg_fn_rate': 0.0,
        }

        # Calculate average rates
        if aggregated['total_tests'] > 0:
            aggregated['avg_fp_rate'] = (aggregated['total_false_positives'] / aggregated['total_tests']) * 100
            aggregated['avg_fn_rate'] = (aggregated['total_false_negatives'] / aggregated['total_tests']) * 100

        return aggregated

    def identify_improvement_opportunities(self, aggregated_stats, all_stats):
        """Identify specific detectors that need improvement."""
        recommendations = []

        # High false positive rate
        if aggregated_stats['avg_fp_rate'] > 5.0:
            recommendations.append({
                'priority': 'HIGH',
                'issue': 'High false positive rate',
                'metric': f"{aggregated_stats['avg_fp_rate']:.1f}%",
                'action': 'Review SECURE scoring - detectors may be too strict or missing context',
                'affected_detectors': 'All detectors with INFO/SECURE findings'
            })

        # High false negative rate
        if aggregated_stats['avg_fn_rate'] > 5.0:
            recommendations.append({
                'priority': 'HIGH',
                'issue': 'High false negative rate',
                'metric': f"{aggregated_stats['avg_fn_rate']:.1f}%",
                'action': 'Review vulnerability detection patterns - may be missing edge cases',
                'affected_detectors': 'All detectors with low severity penalties'
            })

        # Model-specific issues
        model_fp_rates = {}
        for model, stats in all_stats.items():
            if stats['total_tests'] > 0:
                fp_rate = (stats['false_positives'] / stats['total_tests']) * 100
                model_fp_rates[model] = fp_rate

        # Identify models with consistently high FP rates
        high_fp_models = [m for m, rate in model_fp_rates.items() if rate > 10.0]
        if high_fp_models:
            recommendations.append({
                'priority': 'MEDIUM',
                'issue': f'Models with >10% false positive rate: {len(high_fp_models)}',
                'models': high_fp_models[:5],
                'action': 'Investigate if these models generate edge cases that detectors mishandle'
            })

        return recommendations

    def check_convergence(self):
        """Check if refinement has converged."""
        if len(self.iteration_metrics) < 2:
            return False

        current = self.iteration_metrics[-1]
        previous = self.iteration_metrics[-2]

        # Calculate improvement
        fp_improvement = abs(current['avg_fp_rate'] - previous['avg_fp_rate'])
        fn_improvement = abs(current['avg_fn_rate'] - previous['avg_fn_rate'])

        # Converged if improvement is below threshold
        converged = (fp_improvement < self.convergence_threshold and
                    fn_improvement < self.convergence_threshold)

        return converged, fp_improvement, fn_improvement

    def run_iteration(self):
        """Run a single iteration of refinement."""
        print(f"\n{'='*80}")
        print(f"ITERATION {self.iteration + 1} / {self.max_iterations}")
        print(f"{'='*80}\n")

        print(f"Analyzing {len(self.models_to_analyze)} models...\n")

        all_stats = {}

        # Run analysis for each model
        for i, model in enumerate(self.models_to_analyze):
            print(f"[{i+1}/{len(self.models_to_analyze)}] {model}")

            # Run security analysis
            report_path = self.run_analysis_for_model(model)

            if report_path and Path(report_path).exists():
                # Run false positive/negative analysis
                stats = self.run_false_analysis_for_model(model, report_path)
                if stats:
                    all_stats[model] = stats
                    print(f"    FP: {stats['false_positives']}, FN: {stats['false_negatives']}")

            print()

        # Aggregate results
        aggregated = self.aggregate_false_patterns(all_stats)
        self.iteration_metrics.append(aggregated)

        # Generate recommendations
        recommendations = self.identify_improvement_opportunities(aggregated, all_stats)

        # Save iteration results
        self.save_iteration_results(aggregated, recommendations, all_stats)

        # Print summary
        self.print_iteration_summary(aggregated, recommendations)

        return aggregated, recommendations

    def save_iteration_results(self, aggregated, recommendations, all_stats):
        """Save iteration results to JSON."""
        results = {
            'iteration': self.iteration + 1,
            'timestamp': datetime.now().isoformat(),
            'aggregated_stats': aggregated,
            'recommendations': recommendations,
            'model_stats': all_stats
        }

        output_file = self.results_dir / f"iteration_{self.iteration + 1}_results.json"
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)

        print(f"\nResults saved to: {output_file}")

    def print_iteration_summary(self, aggregated, recommendations):
        """Print summary of iteration results."""
        print(f"\n{'='*80}")
        print(f"ITERATION {self.iteration + 1} SUMMARY")
        print(f"{'='*80}")
        print(f"Models Analyzed: {aggregated['models_analyzed']}")
        print(f"Total Tests: {aggregated['total_tests']}")
        print(f"Total False Positives: {aggregated['total_false_positives']} ({aggregated['avg_fp_rate']:.2f}%)")
        print(f"Total False Negatives: {aggregated['total_false_negatives']} ({aggregated['avg_fn_rate']:.2f}%)")

        if recommendations:
            print(f"\nRECOMMENDATIONS ({len(recommendations)}):")
            for i, rec in enumerate(recommendations, 1):
                print(f"\n{i}. [{rec['priority']}] {rec['issue']}")
                if 'metric' in rec:
                    print(f"   Metric: {rec['metric']}")
                print(f"   Action: {rec['action']}")
                if 'affected_detectors' in rec:
                    print(f"   Affected: {rec['affected_detectors']}")

        # Check convergence if we have multiple iterations
        if len(self.iteration_metrics) >= 2:
            converged, fp_imp, fn_imp = self.check_convergence()
            print(f"\nCONVERGENCE CHECK:")
            print(f"  FP Rate Change: {fp_imp:.4f}%")
            print(f"  FN Rate Change: {fn_imp:.4f}%")
            print(f"  Converged: {'YES' if converged else 'NO'} (threshold: {self.convergence_threshold}%)")

    def run(self):
        """Run the complete iterative refinement process."""
        print(f"{'='*80}")
        print("ITERATIVE DETECTOR REFINEMENT FRAMEWORK")
        print(f"{'='*80}")
        print(f"Models to analyze: {len(self.models_to_analyze)}")
        print(f"Max iterations: {self.max_iterations}")
        print(f"Convergence threshold: {self.convergence_threshold}%")
        print()

        for iteration in range(self.max_iterations):
            self.iteration = iteration

            # Run iteration
            aggregated, recommendations = self.run_iteration()

            # Check convergence after iteration 1
            if iteration > 0:
                converged, _, _ = self.check_convergence()
                if converged:
                    print(f"\n{'='*80}")
                    print(f"CONVERGENCE ACHIEVED AFTER {iteration + 1} ITERATIONS")
                    print(f"{'='*80}")
                    break

        # Generate final report
        self.generate_final_report()

    def generate_final_report(self):
        """Generate final refinement report."""
        print(f"\n{'='*80}")
        print("GENERATING FINAL REPORT")
        print(f"{'='*80}")

        report_path = self.results_dir / "final_refinement_report.md"

        with open(report_path, 'w') as f:
            f.write("# Iterative Detector Refinement - Final Report\n\n")
            f.write(f"Generated: {datetime.now().isoformat()}\n\n")

            f.write("## Iterations Performed\n\n")
            for i, metrics in enumerate(self.iteration_metrics, 1):
                f.write(f"### Iteration {i}\n\n")
                f.write(f"- Models Analyzed: {metrics['models_analyzed']}\n")
                f.write(f"- Total Tests: {metrics['total_tests']}\n")
                f.write(f"- False Positives: {metrics['total_false_positives']} ({metrics['avg_fp_rate']:.2f}%)\n")
                f.write(f"- False Negatives: {metrics['total_false_negatives']} ({metrics['avg_fn_rate']:.2f}%)\n\n")

            f.write("## Convergence Analysis\n\n")
            if len(self.iteration_metrics) >= 2:
                initial = self.iteration_metrics[0]
                final = self.iteration_metrics[-1]

                fp_reduction = initial['avg_fp_rate'] - final['avg_fp_rate']
                fn_reduction = initial['avg_fn_rate'] - final['avg_fn_rate']

                f.write(f"- Initial FP Rate: {initial['avg_fp_rate']:.2f}%\n")
                f.write(f"- Final FP Rate: {final['avg_fp_rate']:.2f}%\n")
                f.write(f"- FP Reduction: {fp_reduction:.2f}%\n\n")

                f.write(f"- Initial FN Rate: {initial['avg_fn_rate']:.2f}%\n")
                f.write(f"- Final FN Rate: {final['avg_fn_rate']:.2f}%\n")
                f.write(f"- FN Reduction: {fn_reduction:.2f}%\n")

        print(f"Final report saved to: {report_path}")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description='Iterative detector refinement framework')
    parser.add_argument('--models', nargs='+', help='Specific models to analyze (default: all complete models)')
    parser.add_argument('--max-iterations', type=int, default=5, help='Maximum iterations (default: 5)')
    parser.add_argument('--sample-size', type=int, help='Sample N random models instead of all')

    args = parser.parse_args()

    # Determine which models to analyze
    if args.models:
        models_to_analyze = args.models
    else:
        # Get all complete models
        output_dir = Path("output")
        all_models = []
        for model_dir in output_dir.iterdir():
            if model_dir.is_dir():
                file_count = len(list(model_dir.glob("*")))
                if file_count >= 760:
                    all_models.append(model_dir.name)

        # Sample if requested
        if args.sample_size and args.sample_size < len(all_models):
            import random
            random.seed(42)  # Reproducible sampling
            models_to_analyze = random.sample(all_models, args.sample_size)
        else:
            models_to_analyze = all_models

    print(f"Selected {len(models_to_analyze)} models for analysis")

    # Create and run framework
    framework = IterativeRefinementFramework(
        models_to_analyze=models_to_analyze,
        max_iterations=args.max_iterations
    )

    framework.run()


if __name__ == "__main__":
    main()
