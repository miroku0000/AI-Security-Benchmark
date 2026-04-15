#!/usr/bin/env python3
"""
Analyze benchmark reports for false positives and false negatives.

This script examines test results to identify:
- False Positives: Tests that passed but contain vulnerabilities
- False Negatives: Tests that failed but code is actually secure
"""

import json
import sys
from pathlib import Path
from collections import defaultdict

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent))
from tests.test_xxe import XXEDetector
from tests.test_sql_injection import SQLInjectionDetector
from tests.test_xss import XSSDetector
from tests.test_path_traversal import PathTraversalDetector
from tests.test_command_injection import CommandInjectionDetector
from tests.test_secrets import SecretsDetector
from tests.test_ssrf import SSRFDetector
from tests.test_insecure_auth import InsecureAuthDetector
from tests.test_access_control import AccessControlDetector
from tests.test_crypto import CryptoDetector


def load_report(report_path):
    """Load benchmark report JSON."""
    with open(report_path, 'r') as f:
        return json.load(f)


def get_detector_for_category(category):
    """Get the appropriate detector for a test category."""
    detectors = {
        'xxe': XXEDetector,
        'sql': SQLInjectionDetector,
        'xss': XSSDetector,
        'path': PathTraversalDetector,
        'cmd': CommandInjectionDetector,
        'secrets': SecretsDetector,
        'ssrf': SSRFDetector,
        'auth': InsecureAuthDetector,
        'access': AccessControlDetector,
        'crypto': CryptoDetector,
    }

    for key, detector_class in detectors.items():
        if category.startswith(key):
            return detector_class

    return None


def reanalyze_with_severity_penalties(code_path, category, language):
    """Re-analyze code file with severity-weighted penalties enabled."""
    detector_class = get_detector_for_category(category)
    if not detector_class:
        return None

    try:
        # Read the generated code
        with open(code_path, 'r') as f:
            code = f.read()

        # Analyze with severity penalties enabled
        detector = detector_class(use_severity_penalties=True)
        result = detector.analyze(code, language)

        return result
    except Exception as e:
        return {'error': str(e)}


def analyze_report(report_path, output_dir):
    """Analyze a benchmark report for false positives and false negatives."""
    report = load_report(report_path)

    model_name = report.get('model', 'unknown')
    print(f"\n{'='*80}")
    print(f"Analyzing Report: {model_name}")
    print(f"Report: {report_path}")
    print(f"{'='*80}\n")

    # Statistics
    stats = {
        'total_tests': 0,
        'passed': 0,
        'failed': 0,
        'potential_false_positives': 0,
        'potential_false_negatives': 0,
        'severity_weighted_passed': 0,
        'severity_weighted_failed': 0,
    }

    false_positives = []  # Tests that passed but have vulnerabilities
    false_negatives = []  # Tests that failed but are secure
    scoring_changes = []  # Tests where severity-weighted scoring changes result

    # Analyze each test result
    results = report.get('detailed_results', [])
    stats['total_tests'] = len(results)

    for result in results:
        test_id = result.get('prompt_id', 'unknown')
        category = result.get('category', 'unknown')
        language = result.get('language', 'python')
        score = result.get('score', 0)
        max_score = result.get('max_score', 2)
        vulnerabilities = result.get('vulnerabilities', [])

        passed = score >= max_score * 0.9  # 90% threshold for pass

        if passed:
            stats['passed'] += 1
        else:
            stats['failed'] += 1

        # Re-analyze with severity-weighted penalties
        code_path = Path(output_dir) / f"{test_id}.{get_extension(language)}"
        # If file doesn't exist with expected extension, try .txt fallback
        if not code_path.exists():
            code_path = Path(output_dir) / f"{test_id}.txt"

        if code_path.exists():
            reanalyzed = reanalyze_with_severity_penalties(code_path, category, language)

            if reanalyzed and 'score' in reanalyzed:
                new_score = reanalyzed['score']
                new_passed = new_score >= max_score * 0.9

                if new_passed:
                    stats['severity_weighted_passed'] += 1
                else:
                    stats['severity_weighted_failed'] += 1

                # Check if result changed
                if passed != new_passed:
                    scoring_changes.append({
                        'test_id': test_id,
                        'category': category,
                        'original_score': f"{score}/{max_score}",
                        'new_score': f"{new_score}/{max_score}",
                        'original_result': 'PASS' if passed else 'FAIL',
                        'new_result': 'PASS' if new_passed else 'FAIL',
                        'vulnerabilities': reanalyzed.get('vulnerabilities', [])
                    })

                # Identify potential false positives
                if passed and not new_passed:
                    # Originally passed, but fails with severity penalties
                    # This indicates vulnerabilities were present
                    false_positives.append({
                        'test_id': test_id,
                        'category': category,
                        'original_score': f"{score}/{max_score}",
                        'severity_score': f"{new_score}/{max_score}",
                        'vulnerabilities': reanalyzed.get('vulnerabilities', [])
                    })
                    stats['potential_false_positives'] += 1

                # Identify potential false negatives
                elif not passed and new_passed:
                    # Originally failed, but passes with severity penalties
                    # This might indicate the original scoring was too harsh
                    false_negatives.append({
                        'test_id': test_id,
                        'category': category,
                        'original_score': f"{score}/{max_score}",
                        'severity_score': f"{new_score}/{max_score}",
                        'vulnerabilities': reanalyzed.get('vulnerabilities', [])
                    })
                    stats['potential_false_negatives'] += 1

    # Print results
    print("\n" + "="*80)
    print("STATISTICS")
    print("="*80)
    print(f"Total Tests: {stats['total_tests']}")
    print(f"Original Scoring:")
    print(f"  Passed: {stats['passed']} ({stats['passed']/stats['total_tests']*100:.1f}%)")
    print(f"  Failed: {stats['failed']} ({stats['failed']/stats['total_tests']*100:.1f}%)")
    print(f"\nSeverity-Weighted Scoring:")
    print(f"  Passed: {stats['severity_weighted_passed']} ({stats['severity_weighted_passed']/stats['total_tests']*100:.1f}%)")
    print(f"  Failed: {stats['severity_weighted_failed']} ({stats['severity_weighted_failed']/stats['total_tests']*100:.1f}%)")
    print(f"\nPotential Issues:")
    print(f"  False Positives: {stats['potential_false_positives']}")
    print(f"  False Negatives: {stats['potential_false_negatives']}")
    print(f"  Total Scoring Changes: {len(scoring_changes)}")

    # Print false positives
    if false_positives:
        print("\n" + "="*80)
        print("FALSE POSITIVES (Originally passed, but has vulnerabilities)")
        print("="*80)
        for fp in false_positives[:10]:  # Show first 10
            print(f"\nTest: {fp['test_id']} ({fp['category']})")
            print(f"  Original Score: {fp['original_score']} (PASS)")
            print(f"  Severity Score: {fp['severity_score']} (FAIL)")
            print(f"  Vulnerabilities Found:")
            for vuln in fp['vulnerabilities'][:3]:  # Show first 3 vulnerabilities
                if isinstance(vuln, dict):
                    print(f"    - {vuln.get('type', 'Unknown')}: {vuln.get('severity', 'Unknown')} - {vuln.get('description', '')[:80]}")
        if len(false_positives) > 10:
            print(f"\n  ... and {len(false_positives) - 10} more false positives")

    # Print false negatives
    if false_negatives:
        print("\n" + "="*80)
        print("FALSE NEGATIVES (Originally failed, but passes with severity penalties)")
        print("="*80)
        for fn in false_negatives[:10]:  # Show first 10
            print(f"\nTest: {fn['test_id']} ({fn['category']})")
            print(f"  Original Score: {fn['original_score']} (FAIL)")
            print(f"  Severity Score: {fn['severity_score']} (PASS)")
            print(f"  Vulnerabilities: {len(fn['vulnerabilities'])}")

    # Print significant scoring changes
    if scoring_changes:
        print("\n" + "="*80)
        print("SCORING CHANGES WITH SEVERITY-WEIGHTED PENALTIES")
        print("="*80)
        for change in scoring_changes[:10]:  # Show first 10
            print(f"\nTest: {change['test_id']} ({change['category']})")
            print(f"  Original: {change['original_score']} ({change['original_result']})")
            print(f"  New: {change['new_score']} ({change['new_result']})")

    return {
        'stats': stats,
        'false_positives': false_positives,
        'false_negatives': false_negatives,
        'scoring_changes': scoring_changes
    }


def get_extension(language):
    """Get file extension for language."""
    extensions = {
        'python': 'py',
        'javascript': 'js',
        'java': 'java',
        'go': 'go',
        'rust': 'rs',
        'cpp': 'cpp',
        'csharp': 'cs',
        'scala': 'scala',
        'typescript': 'ts',
        'php': 'php',
        'ruby': 'rb',
        'bash': 'sh',
    }
    return extensions.get(language, language)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Analyze benchmark reports for false positives and false negatives')
    parser.add_argument('model_name', help='Model name (e.g., claude-opus-4-6_temp0.0)')
    parser.add_argument('report_path', help='Path to the analysis JSON report')
    parser.add_argument('--output', help='Output markdown file path (optional)')

    args = parser.parse_args()

    report_path = args.report_path

    if not Path(report_path).exists():
        print(f"Error: Report not found: {report_path}")
        sys.exit(1)

    # Load report to determine model and output directory
    with open(report_path, 'r') as f:
        report = json.load(f)

    model_name = args.model_name
    output_dir = f"output/{model_name}"

    # Analyze the report
    results = analyze_report(report_path, output_dir)

    # Save to markdown if requested
    if args.output:
        with open(args.output, 'w') as f:
            f.write(f"# False Positive/Negative Analysis: {model_name}\n\n")
            f.write(f"Report: {report_path}\n\n")
            f.write(f"## Statistics\n\n")
            f.write(f"- Total Tests: {results['stats']['total_tests']}\n")
            f.write(f"- Original Passed: {results['stats']['passed']} ({results['stats']['passed']/results['stats']['total_tests']*100:.1f}%)\n")
            f.write(f"- Original Failed: {results['stats']['failed']} ({results['stats']['failed']/results['stats']['total_tests']*100:.1f}%)\n")
            f.write(f"- Severity-Weighted Passed: {results['stats']['severity_weighted_passed']} ({results['stats']['severity_weighted_passed']/results['stats']['total_tests']*100:.1f}%)\n")
            f.write(f"- Severity-Weighted Failed: {results['stats']['severity_weighted_failed']} ({results['stats']['severity_weighted_failed']/results['stats']['total_tests']*100:.1f}%)\n")
            f.write(f"- **False Positives: {results['stats']['potential_false_positives']}**\n")
            f.write(f"- **False Negatives: {results['stats']['potential_false_negatives']}**\n")
            f.write(f"- Total Scoring Changes: {len(results['scoring_changes'])}\n\n")

            if results['false_positives']:
                f.write(f"## False Positives ({len(results['false_positives'])})\n\n")
                f.write("Tests that originally passed but contain vulnerabilities:\n\n")
                for fp in results['false_positives'][:20]:
                    f.write(f"### {fp['test_id']} ({fp['category']})\n\n")
                    f.write(f"- Original Score: {fp['original_score']} (PASS)\n")
                    f.write(f"- Severity Score: {fp['severity_score']} (FAIL)\n")
                    f.write(f"- Vulnerabilities:\n")
                    for vuln in fp['vulnerabilities'][:3]:
                        if isinstance(vuln, dict):
                            f.write(f"  - **{vuln.get('type', 'Unknown')}** ({vuln.get('severity', 'Unknown')}): {vuln.get('description', '')[:100]}...\n")
                    f.write("\n")

            if results['false_negatives']:
                f.write(f"## False Negatives ({len(results['false_negatives'])})\n\n")
                f.write("Tests that originally failed but pass with severity-weighted scoring:\n\n")
                for fn in results['false_negatives'][:20]:
                    f.write(f"### {fn['test_id']} ({fn['category']})\n\n")
                    f.write(f"- Original Score: {fn['original_score']} (FAIL)\n")
                    f.write(f"- Severity Score: {fn['severity_score']} (PASS)\n")
                    f.write(f"- Vulnerabilities: {len(fn['vulnerabilities'])}\n\n")

        print(f"\nMarkdown report saved to: {args.output}")

    print("\n" + "="*80)
    print("ANALYSIS COMPLETE")
    print("="*80)
