#!/usr/bin/env python3
"""
Temperature Impact Analysis

Analyzes how temperature settings affect vulnerability rates in AI-generated code.
Compares the same model at different temperatures to understand the security implications.

Usage:
  python3 analysis/analyze_temperature_impact.py
  python3 analysis/analyze_temperature_impact.py --model gpt-4o
  python3 analysis/analyze_temperature_impact.py --output analysis/temp_impact_report.txt
"""
import argparse
import json
import logging
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)


class TemperatureImpactAnalyzer:
    """Analyzes temperature impact on code security."""

    def __init__(self, reports_dir: str = "reports"):
        self.reports_dir = Path(reports_dir)
        self.reports_by_model = defaultdict(list)

    def load_reports(self) -> int:
        """Load all JSON reports that have temperature data."""
        count = 0
        for report_file in self.reports_dir.glob("*.json"):
            try:
                with open(report_file, 'r') as f:
                    report = json.load(f)

                # Only process reports with temperature data
                if 'temperature' in report and report['temperature'] is not None:
                    model_name = report.get('model_name', 'Unknown')
                    temp = report['temperature']

                    self.reports_by_model[model_name].append({
                        'temperature': temp,
                        'report_file': str(report_file),
                        'report': report
                    })
                    count += 1
            except Exception as e:
                logger.warning("Error loading %s: %s", report_file, e)

        # Sort reports by temperature for each model
        for model in self.reports_by_model:
            self.reports_by_model[model].sort(key=lambda x: x['temperature'])

        logger.info("Loaded %d reports with temperature data for %d models",
                   count, len(self.reports_by_model))
        return count

    def _extract_vulnerability_stats(self, report: Dict) -> Dict:
        """Extract vulnerability statistics from a report."""
        summary = report.get('summary', {})

        # Overall stats
        stats = {
            'total_tests': summary.get('completed_tests', 0),
            'secure': summary.get('secure', 0),
            'partial': summary.get('partial', 0),
            'vulnerable': summary.get('vulnerable', 0),
            'percentage': summary.get('percentage', 0.0),
            'score': summary.get('overall_score', 'N/A'),
        }

        # Vulnerability breakdown by type
        vuln_types = defaultdict(int)
        for result in report.get('detailed_results', []):
            for vuln in result.get('vulnerabilities', []):
                if vuln['type'] != 'SECURE':
                    vuln_type = vuln['type']
                    vuln_types[vuln_type] += 1

        stats['vulnerability_types'] = dict(vuln_types)

        # Category breakdown
        stats['categories'] = report.get('categories', {})

        return stats

    def analyze_model(self, model_name: str) -> Dict:
        """Analyze temperature impact for a specific model."""
        if model_name not in self.reports_by_model:
            return None

        reports = self.reports_by_model[model_name]
        if len(reports) < 2:
            logger.warning("Model %s has only %d temperature variant (need at least 2 for comparison)",
                          model_name, len(reports))
            return None

        analysis = {
            'model': model_name,
            'temperature_variants': []
        }

        for report_data in reports:
            temp = report_data['temperature']
            report = report_data['report']
            stats = self._extract_vulnerability_stats(report)

            analysis['temperature_variants'].append({
                'temperature': temp,
                'stats': stats,
                'report_file': report_data['report_file']
            })

        # Calculate temperature impact metrics
        analysis['impact'] = self._calculate_impact(analysis['temperature_variants'])

        return analysis

    def _calculate_impact(self, variants: List[Dict]) -> Dict:
        """Calculate how temperature affects security metrics."""
        if len(variants) < 2:
            return {}

        temps = [v['temperature'] for v in variants]
        percentages = [v['stats']['percentage'] for v in variants]
        vulnerables = [v['stats']['vulnerable'] for v in variants]

        # Calculate correlation between temperature and vulnerability rate
        # Higher temperature -> more vulnerable? Or less?
        temp_range = max(temps) - min(temps)
        percentage_change = max(percentages) - min(percentages)
        vulnerable_change = max(vulnerables) - min(vulnerables)

        # Find best and worst temperatures
        best_idx = percentages.index(max(percentages))
        worst_idx = percentages.index(min(percentages))

        return {
            'temperature_range': f"{min(temps):.1f} - {max(temps):.1f}",
            'percentage_change': round(percentage_change, 2),
            'vulnerable_count_change': vulnerable_change,
            'best_temperature': temps[best_idx],
            'best_percentage': percentages[best_idx],
            'worst_temperature': temps[worst_idx],
            'worst_percentage': percentages[worst_idx],
            'trend': 'higher_temp_worse' if temps[worst_idx] > temps[best_idx] else 'lower_temp_worse'
        }

    def generate_report(self, model_filter: str = None) -> str:
        """Generate temperature impact report."""
        output = []
        output.append("=" * 80)
        output.append("TEMPERATURE IMPACT ANALYSIS")
        output.append("=" * 80)
        output.append("")
        output.append("This report analyzes how temperature settings affect security in AI-generated code.")
        output.append("Lower security score = more vulnerabilities.")
        output.append("")

        models_to_analyze = [model_filter] if model_filter else sorted(self.reports_by_model.keys())

        analyzed_count = 0
        for model_name in models_to_analyze:
            if model_name not in self.reports_by_model:
                if model_filter:
                    output.append(f"No temperature data found for model: {model_name}")
                continue

            analysis = self.analyze_model(model_name)
            if not analysis:
                continue

            analyzed_count += 1

            output.append("=" * 80)
            output.append(f"MODEL: {model_name}")
            output.append("=" * 80)
            output.append("")

            # Temperature variants summary
            output.append("Temperature Variants:")
            output.append(f"{'Temp':<8} {'Score':<15} {'Secure':<8} {'Partial':<8} {'Vulnerable':<12} {'Percentage':<10}")
            output.append("-" * 80)

            for variant in analysis['temperature_variants']:
                temp = variant['temperature']
                stats = variant['stats']
                output.append(f"{temp:<8.1f} {stats['score']:<15} {stats['secure']:<8} "
                            f"{stats['partial']:<8} {stats['vulnerable']:<12} {stats['percentage']:<10.1f}%")

            output.append("")

            # Impact summary
            if 'impact' in analysis and analysis['impact']:
                impact = analysis['impact']
                output.append("Impact Summary:")
                output.append(f"  Temperature Range: {impact['temperature_range']}")
                output.append(f"  Security Score Change: {impact['percentage_change']:.1f} percentage points")
                output.append(f"  Vulnerable Count Change: {impact['vulnerable_count_change']}")
                output.append(f"  Best Performance: {impact['best_temperature']:.1f} ({impact['best_percentage']:.1f}%)")
                output.append(f"  Worst Performance: {impact['worst_temperature']:.1f} ({impact['worst_percentage']:.1f}%)")

                # Interpretation
                if impact['trend'] == 'higher_temp_worse':
                    output.append(f"  → Higher temperature appears to INCREASE vulnerabilities for this model")
                else:
                    output.append(f"  → Lower temperature appears to INCREASE vulnerabilities for this model")

            output.append("")

            # Vulnerability type comparison
            output.append("Vulnerability Types by Temperature:")
            all_vuln_types = set()
            for variant in analysis['temperature_variants']:
                all_vuln_types.update(variant['stats']['vulnerability_types'].keys())

            if all_vuln_types:
                output.append(f"{'Vuln Type':<35} " +
                            " ".join([f"T={v['temperature']:.1f}" for v in analysis['temperature_variants']]))
                output.append("-" * 80)

                for vuln_type in sorted(all_vuln_types):
                    counts = []
                    for variant in analysis['temperature_variants']:
                        count = variant['stats']['vulnerability_types'].get(vuln_type, 0)
                        counts.append(f"{count:>6}")
                    output.append(f"{vuln_type:<35} " + " ".join(counts))

            output.append("")

        # Overall summary
        if analyzed_count == 0:
            output.append("=" * 80)
            output.append("No models found with multiple temperature variants for comparison.")
            output.append("Run benchmarks at different temperatures to enable temperature impact analysis:")
            output.append("")
            output.append("  python3 auto_benchmark.py --model gpt-4o --temperature 0.2")
            output.append("  python3 auto_benchmark.py --model gpt-4o --temperature 0.5")
            output.append("  python3 auto_benchmark.py --model gpt-4o --temperature 0.7")
            output.append("  python3 auto_benchmark.py --model gpt-4o --temperature 1.0")
            output.append("")
        else:
            output.append("=" * 80)
            output.append(f"SUMMARY: Analyzed {analyzed_count} model(s) with temperature variants")
            output.append("=" * 80)

        return "\n".join(output)


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)-8s %(message)s",
    )

    parser = argparse.ArgumentParser(
        description="Analyze temperature impact on code security",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze all models
  python3 analysis/analyze_temperature_impact.py

  # Analyze specific model
  python3 analysis/analyze_temperature_impact.py --model gpt-4o

  # Save to file
  python3 analysis/analyze_temperature_impact.py --output temp_analysis.txt
        """
    )

    parser.add_argument(
        '--model',
        type=str,
        help='Analyze specific model only'
    )
    parser.add_argument(
        '--reports-dir',
        type=str,
        default='reports',
        help='Directory containing JSON reports (default: reports)'
    )
    parser.add_argument(
        '--output',
        type=str,
        help='Save report to file (otherwise prints to console)'
    )

    args = parser.parse_args()

    analyzer = TemperatureImpactAnalyzer(reports_dir=args.reports_dir)

    report_count = analyzer.load_reports()
    if report_count == 0:
        logger.error("No reports with temperature data found in %s", args.reports_dir)
        logger.info("Run benchmarks with temperature parameter to generate data:")
        logger.info("  python3 auto_benchmark.py --model <model> --temperature <temp>")
        return 1

    report_text = analyzer.generate_report(model_filter=args.model)

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            f.write(report_text)
        logger.info("Report saved to: %s", args.output)
    else:
        print(report_text)

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
