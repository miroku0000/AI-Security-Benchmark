#!/usr/bin/env python3
"""
Analyze False Positive/Negative Patterns

Examines false results across multiple models to identify systematic detector issues.
Generates specific, actionable recommendations for detector improvements.
"""
import json
import re
from pathlib import Path
from collections import defaultdict, Counter

class FalsePatternAnalyzer:
    def __init__(self, refinement_dir="reports/refinement"):
        self.refinement_dir = Path(refinement_dir)
        self.false_positive_patterns = defaultdict(list)
        self.false_negative_patterns = defaultdict(list)

    def load_iteration_results(self, iteration=1):
        """Load results from a specific iteration."""
        results_file = self.refinement_dir / f"iteration_{iteration}_results.json"

        if not results_file.exists():
            print(f"No results found for iteration {iteration}")
            return None

        with open(results_file, 'r') as f:
            return json.load(f)

    def analyze_false_positive_patterns(self, models):
        """
        Analyze false positives to identify common patterns.

        False Positive = Test passed but contains vulnerabilities
        This indicates: Detector gave too much credit for SECURE patterns
                       or ignored CRITICAL/HIGH vulnerabilities
        """
        patterns = {
            'info_secure_dominates': [],  # SECURE/INFO findings outweigh real vulnerabilities
            'severity_underweighted': [],  # CRITICAL/HIGH vulns not penalized enough
            'context_missing': [],  # Detector missing context that makes code vulnerable
            'edge_cases': [],  # Uncommon code patterns not handled properly
        }

        # Load all false analysis markdown files
        for model in models:
            fp_file = self.refinement_dir / f"{model}_false_analysis_iter1.md"
            if not fp_file.exists():
                continue

            with open(fp_file, 'r') as f:
                content = f.read()

            # Extract false positive entries
            fp_section = self.extract_section(content, "## False Positives")
            if not fp_section:
                continue

            # Parse each false positive case
            cases = self.parse_false_cases(fp_section)

            for case in cases:
                test_id = case.get('test_id', '')
                category = case.get('category', '')
                vulnerabilities = case.get('vulnerabilities', [])

                # Analyze pattern
                has_secure = any('SECURE' in str(v) or 'INFO' in str(v) for v in vulnerabilities)
                has_critical = any('CRITICAL' in str(v) for v in vulnerabilities)
                has_high = any('HIGH' in str(v) for v in vulnerabilities)

                if has_secure and (has_critical or has_high):
                    # SECURE findings outweighed critical vulnerabilities
                    patterns['info_secure_dominates'].append({
                        'model': model,
                        'test_id': test_id,
                        'category': category,
                        'issue': 'SECURE/INFO findings gave too much credit despite CRITICAL/HIGH vulns'
                    })

                if has_critical or has_high:
                    # Severity not weighted heavily enough
                    patterns['severity_underweighted'].append({
                        'model': model,
                        'test_id': test_id,
                        'category': category,
                        'issue': f'{"CRITICAL" if has_critical else "HIGH"} vulnerability not penalized enough'
                    })

        return patterns

    def extract_section(self, content, section_header):
        """Extract content between section headers."""
        lines = content.split('\n')
        in_section = False
        section_lines = []

        for line in lines:
            if line.startswith(section_header):
                in_section = True
                continue
            elif line.startswith('##') and in_section:
                # Reached next section
                break
            elif in_section:
                section_lines.append(line)

        return '\n'.join(section_lines)

    def parse_false_cases(self, section_content):
        """Parse individual false positive/negative cases from section."""
        cases = []
        current_case = {}

        lines = section_content.split('\n')

        for line in lines:
            # New case starts with ###
            if line.startswith('###'):
                if current_case:
                    cases.append(current_case)
                current_case = {}

                # Extract test_id and category
                match = re.match(r'### (\S+) \(([^)]+)\)', line)
                if match:
                    current_case['test_id'] = match.group(1)
                    current_case['category'] = match.group(2)

            # Extract vulnerabilities
            elif line.strip().startswith('- **') and current_case:
                if 'vulnerabilities' not in current_case:
                    current_case['vulnerabilities'] = []
                current_case['vulnerabilities'].append(line.strip())

        # Add last case
        if current_case:
            cases.append(current_case)

        return cases

    def generate_detector_improvements(self, patterns):
        """Generate specific detector improvement recommendations."""
        improvements = []

        # Issue 1: SECURE findings outweigh critical vulns
        if patterns['info_secure_dominates']:
            affected_categories = Counter(p['category'] for p in patterns['info_secure_dominates'])

            improvements.append({
                'issue': 'SECURE/INFO findings prevent failing tests with critical vulnerabilities',
                'frequency': len(patterns['info_secure_dominates']),
                'affected_categories': dict(affected_categories.most_common(5)),
                'recommendation': [
                    'Reduce positive score contribution from SECURE/INFO findings',
                    'Current issue: test_xxe.py gives +1 point for secure configs but only -0.5 for XXE',
                    'Suggested fix: SECURE should give +0.5, INFO should give +0.1',
                    'Alternative: Change to penalty-only scoring - start at max points, subtract for vulns'
                ],
                'priority': 'CRITICAL',
                'affected_files': [
                    'tests/test_xxe.py',
                    'tests/test_sql_injection.py',
                    'tests/test_xss.py',
                    'tests/test_crypto.py'
                ]
            })

        # Issue 2: Severity penalties too weak
        if patterns['severity_underweighted']:
            affected_categories = Counter(p['category'] for p in patterns['severity_underweighted'])

            improvements.append({
                'issue': 'CRITICAL and HIGH severity vulnerabilities not penalized heavily enough',
                'frequency': len(patterns['severity_underweighted']),
                'affected_categories': dict(affected_categories.most_common(5)),
                'recommendation': [
                    'Increase severity multipliers:',
                    '  - CRITICAL: 2.0 → 4.0 (auto-fail if any CRITICAL found)',
                    '  - HIGH: 1.5 → 3.0',
                    '  - MEDIUM: 1.0 → 1.5',
                    '  - LOW: 0.5 → 0.5 (no change)',
                    'Implement auto-fail logic: if CRITICAL found, score = 0 regardless of SECURE findings'
                ],
                'priority': 'CRITICAL',
                'affected_files': 'All detector files'
            })

        return improvements

    def generate_report(self, improvements, output_file="reports/refinement/detector_improvement_recommendations.md"):
        """Generate markdown report with improvement recommendations."""
        with open(output_file, 'w') as f:
            f.write("# Detector Improvement Recommendations\n\n")
            f.write("Generated from analysis of false positives/negatives across multiple models.\n\n")

            f.write("## Summary\n\n")
            f.write(f"Total Improvement Areas Identified: {len(improvements)}\n\n")

            for i, imp in enumerate(improvements, 1):
                f.write(f"## {i}. {imp['issue']}\n\n")
                f.write(f"**Priority:** {imp['priority']}\n\n")
                f.write(f"**Frequency:** {imp['frequency']} occurrences\n\n")

                if 'affected_categories' in imp:
                    f.write("**Affected Categories:**\n\n")
                    for cat, count in imp['affected_categories'].items():
                        f.write(f"- {cat}: {count} cases\n")
                    f.write("\n")

                f.write("**Recommendations:**\n\n")
                for rec in imp['recommendation']:
                    f.write(f"- {rec}\n")
                f.write("\n")

                if 'affected_files' in imp:
                    f.write("**Files to Modify:**\n\n")
                    if isinstance(imp['affected_files'], list):
                        for file in imp['affected_files']:
                            f.write(f"- {file}\n")
                    else:
                        f.write(f"- {imp['affected_files']}\n")
                    f.write("\n")

        print(f"Report saved to: {output_file}")

    def run(self, iteration=1):
        """Run the pattern analysis."""
        print("="*80)
        print("FALSE PATTERN ANALYZER")
        print("="*80)

        # Load iteration results
        results = self.load_iteration_results(iteration)
        if not results:
            return

        models = list(results['model_stats'].keys())
        print(f"\nAnalyzing {len(models)} models from iteration {iteration}\n")

        # Analyze false positive patterns
        print("Analyzing false positive patterns...")
        fp_patterns = self.analyze_false_positive_patterns(models)

        # Count patterns
        total_fp_patterns = sum(len(v) for v in fp_patterns.values())
        print(f"  Found {total_fp_patterns} false positive pattern instances")

        for pattern_type, instances in fp_patterns.items():
            if instances:
                print(f"    - {pattern_type}: {len(instances)}")

        # Generate improvements
        print("\nGenerating improvement recommendations...")
        improvements = self.generate_detector_improvements(fp_patterns)
        print(f"  Generated {len(improvements)} improvement recommendations")

        # Generate report
        self.generate_report(improvements)

        return improvements


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Analyze false positive/negative patterns')
    parser.add_argument('--iteration', type=int, default=1, help='Iteration number to analyze')

    args = parser.parse_args()

    analyzer = FalsePatternAnalyzer()
    analyzer.run(iteration=args.iteration)
