#!/usr/bin/env python3
"""
Detector Accuracy Analyzer

Analyzes false positives and false negatives in the benchmark to identify
areas where detectors need improvement.

This tool processes FP/FN analysis reports and provides actionable insights:
1. Which tests have the most detector errors
2. Which vulnerability categories need improvement
3. Specific code patterns the detector misses or over-flags
4. Recommendations for detector improvements
"""

import json
import argparse
from pathlib import Path
from typing import Dict, List
from collections import defaultdict, Counter
from datetime import datetime


class DetectorAccuracyAnalyzer:
    """Analyzes detector false positives and false negatives."""

    def __init__(self, report_path: str):
        """
        Initialize analyzer with FP/FN analysis report.

        Args:
            report_path: Path to fp_fn_analysis_*.json file
        """
        self.report_path = Path(report_path)

        with open(self.report_path) as f:
            self.data = json.load(f)

        self.false_positives = self.data.get('false_positives', [])
        self.false_negatives = self.data.get('false_negatives', [])
        self.inconsistent = self.data.get('inconsistent_detection', [])
        self.summary = self.data.get('summary', {})

    def print_overview(self):
        """Print high-level overview of detector accuracy."""
        total_tests = self.summary.get('total_tests', 0)
        fp_count = self.summary.get('fp_count', 0)
        fn_count = self.summary.get('fn_count', 0)
        inconsistent_count = self.summary.get('inconsistent_count', 0)
        clean_count = self.summary.get('clean_tests', 0)

        print("\n" + "="*80)
        print("DETECTOR ACCURACY OVERVIEW")
        print("="*80)
        print(f"Total Tests:           {total_tests}")
        print(f"Clean (No Issues):     {clean_count:3d} ({clean_count/max(total_tests,1)*100:.1f}%)")
        print(f"False Positives:       {fp_count:3d} ({fp_count/max(total_tests,1)*100:.1f}%)")
        print(f"False Negatives:       {fn_count:3d} ({fn_count/max(total_tests,1)*100:.1f}%)")
        print(f"Inconsistent:          {inconsistent_count:3d} ({inconsistent_count/max(total_tests,1)*100:.1f}%)")
        print("="*80)

        # Calculate detector accuracy
        correct = total_tests - fp_count - fn_count - inconsistent_count
        accuracy = correct / max(total_tests, 1)

        print(f"\nDetector Accuracy:     {accuracy:.1%}")
        print(f"Error Rate:            {(fp_count + fn_count)/max(total_tests,1):.1%}")
        print()

    def analyze_by_category(self):
        """Analyze FP/FN breakdown by vulnerability category."""
        print("\n" + "="*80)
        print("FALSE POSITIVES BY CATEGORY")
        print("="*80)

        fp_by_cat = defaultdict(list)
        for fp in self.false_positives:
            fp_by_cat[fp['category']].append(fp)

        if not fp_by_cat:
            print("None found!\n")
        else:
            for cat, fps in sorted(fp_by_cat.items(), key=lambda x: len(x[1]), reverse=True):
                test_ids = [fp['test_id'] for fp in fps]
                consensus_pct = fps[0]['consensus']['agreement_rate']

                print(f"\n{cat}:")
                print(f"  Count: {len(fps)} tests")
                print(f"  Tests: {', '.join(test_ids)}")
                print(f"  Consensus: {consensus_pct:.1%} of models generate secure code")
                print(f"  Issue: Detector flags as VULNERABLE but models agree it's SECURE")

        print("\n" + "="*80)
        print("FALSE NEGATIVES BY CATEGORY")
        print("="*80)

        fn_by_cat = defaultdict(list)
        for fn in self.false_negatives:
            fn_by_cat[fn['category']].append(fn)

        if not fn_by_cat:
            print("None found!\n")
        else:
            for cat, fns in sorted(fn_by_cat.items(), key=lambda x: len(x[1]), reverse=True):
                test_ids = [fn['test_id'] for fn in fns]
                consensus_pct = fns[0]['consensus']['agreement_rate']

                print(f"\n{cat}:")
                print(f"  Count: {len(fns)} tests")
                print(f"  Tests: {', '.join(test_ids)}")
                print(f"  Consensus: {consensus_pct:.1%} of models generate VULNERABLE code")
                print(f"  Issue: Detector says SECURE but models agree it's VULNERABLE")

        print()

    def find_high_priority_fixes(self, min_outliers: int = 3):
        """
        Identify high-priority detector fixes.

        Args:
            min_outliers: Minimum number of outlier models to consider high priority

        Returns:
            List of high-priority fix recommendations
        """
        print("\n" + "="*80)
        print("HIGH-PRIORITY DETECTOR FIXES")
        print("="*80)
        print(f"(Tests where {min_outliers}+ models disagree with detector)\n")

        priority_fixes = []

        # High-priority false positives
        for fp in self.false_positives:
            outlier_count = len(fp.get('outliers', []))
            consensus = fp['consensus']['agreement_rate']

            if outlier_count >= min_outliers and consensus >= 0.7:
                priority_fixes.append({
                    'type': 'FALSE_POSITIVE',
                    'test_id': fp['test_id'],
                    'category': fp['category'],
                    'outlier_count': outlier_count,
                    'consensus': consensus,
                    'severity': fp.get('severity', 'UNKNOWN'),
                    'outlier_models': [o['model'] for o in fp['outliers'][:5]]
                })

        # High-priority false negatives
        for fn in self.false_negatives:
            outlier_count = len(fn.get('outliers', []))
            consensus = fn['consensus']['agreement_rate']

            if outlier_count >= min_outliers and consensus >= 0.7:
                priority_fixes.append({
                    'type': 'FALSE_NEGATIVE',
                    'test_id': fn['test_id'],
                    'category': fn['category'],
                    'outlier_count': outlier_count,
                    'consensus': consensus,
                    'severity': fn.get('severity', 'UNKNOWN'),
                    'outlier_models': [o['model'] for o in fn['outliers'][:5]]
                })

        # Sort by outlier count
        priority_fixes.sort(key=lambda x: x['outlier_count'], reverse=True)

        if not priority_fixes:
            print("None found! Detector is performing well.\n")
            return []

        for i, fix in enumerate(priority_fixes, 1):
            print(f"{i}. {fix['test_id']} ({fix['category']}) - {fix['type']}")
            print(f"   Outliers: {fix['outlier_count']} models")
            print(f"   Consensus: {fix['consensus']:.1%}")
            print(f"   Severity: {fix['severity']}")
            print(f"   Example models: {', '.join(fix['outlier_models'][:3])}")
            print()

        return priority_fixes

    def examine_test_details(self, test_id: str):
        """
        Examine detailed information about a specific test.

        Args:
            test_id: Test ID to examine (e.g., "access_001")
        """
        print("\n" + "="*80)
        print(f"TEST DETAILS: {test_id}")
        print("="*80)

        # Find test in FP/FN/inconsistent
        test_data = None
        test_type = None

        for fp in self.false_positives:
            if fp['test_id'] == test_id:
                test_data = fp
                test_type = "FALSE POSITIVE"
                break

        if not test_data:
            for fn in self.false_negatives:
                if fn['test_id'] == test_id:
                    test_data = fn
                    test_type = "FALSE NEGATIVE"
                    break

        if not test_data:
            for inc in self.inconsistent:
                if inc['test_id'] == test_id:
                    test_data = inc
                    test_type = "INCONSISTENT"
                    break

        if not test_data:
            print(f"Test {test_id} not found in FP/FN/inconsistent lists.")
            print("This test may be 'clean' (detector agrees with model consensus).")
            return

        print(f"\nType: {test_type}")
        print(f"Category: {test_data['category']}")
        print(f"Severity: {test_data.get('severity', 'UNKNOWN')}")

        consensus = test_data.get('consensus', {})
        print(f"\nModel Consensus:")
        print(f"  Total Models: {consensus.get('total_models', 0)}")
        print(f"  Secure: {consensus.get('secure', 0)}")
        print(f"  Partial: {consensus.get('partial', 0)}")
        print(f"  Vulnerable: {consensus.get('vulnerable', 0)}")
        print(f"  Majority: {consensus.get('majority', 'UNKNOWN')}")
        print(f"  Agreement Rate: {consensus.get('agreement_rate', 0):.1%}")

        outliers = test_data.get('outliers', [])
        if outliers:
            print(f"\nOutlier Models ({len(outliers)}):")
            for outlier in outliers[:10]:  # Show first 10
                model = outlier.get('model', 'unknown')
                score = outlier.get('score', 0)
                max_score = outlier.get('max_score', 0)
                vulns = outlier.get('vulnerabilities', [])

                print(f"\n  {model}: {score}/{max_score}")
                if vulns:
                    for vuln in vulns[:2]:  # First 2 vulnerabilities
                        vuln_type = vuln.get('type', 'UNKNOWN')
                        desc = vuln.get('description', 'No description')[:100]
                        print(f"    - {vuln_type}: {desc}...")

        print()

    def generate_recommendations(self):
        """Generate specific recommendations for improving detectors."""
        print("\n" + "="*80)
        print("RECOMMENDATIONS FOR DETECTOR IMPROVEMENTS")
        print("="*80)

        recommendations = []

        # Analyze false positives
        fp_by_cat = defaultdict(list)
        for fp in self.false_positives:
            fp_by_cat[fp['category']].append(fp)

        for category, fps in fp_by_cat.items():
            if len(fps) == 0:
                continue

            # Look for common patterns in outlier vulnerabilities
            all_vuln_types = []
            all_descriptions = []

            for fp in fps:
                for outlier in fp.get('outliers', []):
                    for vuln in outlier.get('vulnerabilities', []):
                        all_vuln_types.append(vuln.get('type', 'UNKNOWN'))
                        all_descriptions.append(vuln.get('description', ''))

            # Count vulnerability types
            vuln_counter = Counter(all_vuln_types)
            most_common = vuln_counter.most_common(3)

            recommendation = {
                'category': category,
                'issue_type': 'FALSE_POSITIVE',
                'test_count': len(fps),
                'test_ids': [fp['test_id'] for fp in fps],
                'common_patterns': most_common,
                'suggestion': self._generate_fp_suggestion(category, all_descriptions)
            }
            recommendations.append(recommendation)

        # Analyze false negatives
        fn_by_cat = defaultdict(list)
        for fn in self.false_negatives:
            fn_by_cat[fn['category']].append(fn)

        for category, fns in fn_by_cat.items():
            if len(fns) == 0:
                continue

            recommendation = {
                'category': category,
                'issue_type': 'FALSE_NEGATIVE',
                'test_count': len(fns),
                'test_ids': [fn['test_id'] for fn in fns],
                'suggestion': self._generate_fn_suggestion(category, fns)
            }
            recommendations.append(recommendation)

        # Print recommendations
        for i, rec in enumerate(recommendations, 1):
            print(f"\n{i}. {rec['category']} - {rec['issue_type']}")
            print(f"   Affected Tests: {', '.join(rec['test_ids'])}")
            if 'common_patterns' in rec:
                print(f"   Common Patterns:")
                for pattern, count in rec['common_patterns']:
                    print(f"     - {pattern} ({count}x)")
            print(f"   Suggestion: {rec['suggestion']}")

        print()

        return recommendations

    def _generate_fp_suggestion(self, category: str, descriptions: List[str]) -> str:
        """Generate suggestion for fixing false positives."""
        combined = ' '.join(descriptions).lower()

        if category == 'broken_access_control':
            if 'decorator' in combined or '@' in combined:
                return "Add decorator pattern recognition (@require_owner, @permission_required)"
            elif 'ownership' in combined or 'user_id' in combined:
                return "Improve ownership check detection (user_id ==, owner field comparison)"
            elif 'filter' in combined:
                return "Add queryset filtering recognition (Model.filter(user=current_user))"
            else:
                return "Review access control patterns - detector may be too strict"

        elif category == 'insecure_crypto':
            if 'md5' in combined and ('checksum' in combined or 'etag' in combined):
                return "Add context-aware MD5 detection (allow for checksums/ETags, flag for passwords)"
            elif 'sha256' in combined and 'password' in combined:
                return "Distinguish SHA-256 for passwords (need bcrypt) vs file hashing (OK)"
            else:
                return "Improve crypto context detection"

        elif category == 'xss':
            if 'textcontent' in combined:
                return "Recognize .textContent as safe (not .innerHTML)"
            elif 'sanitize' in combined or 'dompurify' in combined:
                return "Add sanitization library detection (DOMPurify, sanitize-html)"
            else:
                return "Improve XSS safe pattern recognition"

        elif category == 'sql_injection':
            if 'parameterized' in combined or 'prepared' in combined:
                return "Improve parameterized query detection"
            else:
                return "Review SQL injection patterns"

        elif category == 'path_traversal':
            if 'abspath' in combined or 'realpath' in combined:
                return "Add path normalization + containment check detection"
            else:
                return "Improve path traversal safe pattern recognition"

        elif category == 'command_injection':
            if 'list' in combined or 'array' in combined:
                return "Recognize subprocess with list arguments (safe)"
            else:
                return "Improve command injection safe pattern recognition"

        else:
            return "Review detector patterns for this category"

    def _generate_fn_suggestion(self, category: str, fns: List[Dict]) -> str:
        """Generate suggestion for fixing false negatives."""
        # Detector is missing vulnerabilities that most models introduce
        return f"Detector may be too permissive - {len(fns)} tests where most models generate vulnerable code but detector says secure"

    def save_detailed_report(self, output_path: str):
        """Save detailed analysis report to file."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        report = {
            'analysis_date': datetime.now().isoformat(),
            'source_report': str(self.report_path),
            'summary': self.summary,
            'false_positives_by_category': self._group_by_category(self.false_positives),
            'false_negatives_by_category': self._group_by_category(self.false_negatives),
            'high_priority_fixes': self.find_high_priority_fixes(min_outliers=3),
            'recommendations': self.generate_recommendations()
        }

        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)

        print(f"\nDetailed report saved to: {output_path}")

    def _group_by_category(self, items: List[Dict]) -> Dict:
        """Group items by category."""
        by_cat = defaultdict(list)
        for item in items:
            by_cat[item['category']].append(item['test_id'])
        return dict(by_cat)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Analyze detector accuracy (false positives/negatives)'
    )
    parser.add_argument(
        '--report', '-r',
        type=str,
        help='Path to fp_fn_analysis_*.json file'
    )
    parser.add_argument(
        '--test', '-t',
        type=str,
        help='Examine specific test ID (e.g., access_001)'
    )
    parser.add_argument(
        '--output', '-o',
        type=str,
        default='reports/detector_accuracy_report.json',
        help='Output path for detailed report'
    )
    parser.add_argument(
        '--min-outliers',
        type=int,
        default=3,
        help='Minimum outlier count for high-priority fixes (default: 3)'
    )

    args = parser.parse_args()

    # Find latest FP/FN analysis if not specified
    if not args.report:
        reports_dir = Path('reports')
        fp_fn_reports = sorted(reports_dir.glob('fp_fn_analysis_*.json'))

        if not fp_fn_reports:
            print("ERROR: No FP/FN analysis reports found in reports/")
            print("   Run: python3 analyze_fp_fn_across_models.py")
            return 1

        args.report = str(fp_fn_reports[-1])
        print(f"Using latest report: {args.report}\n")

    # Initialize analyzer
    try:
        analyzer = DetectorAccuracyAnalyzer(args.report)
    except FileNotFoundError:
        print(f"ERROR: Report not found: {args.report}")
        return 1
    except json.JSONDecodeError:
        print(f"ERROR: Invalid JSON in report: {args.report}")
        return 1

    # If specific test requested, show only that
    if args.test:
        analyzer.examine_test_details(args.test)
        return 0

    # Otherwise, show full analysis
    analyzer.print_overview()
    analyzer.analyze_by_category()
    analyzer.find_high_priority_fixes(min_outliers=args.min_outliers)
    analyzer.generate_recommendations()

    # Save detailed report
    if args.output:
        analyzer.save_detailed_report(args.output)

    return 0


if __name__ == "__main__":
    exit(main())
