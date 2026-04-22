#!/usr/bin/env python3
"""
Analyze false negatives in CodeLlama results to identify missing detection patterns.
Provides detailed feedback for iterative detector refinement.
"""

import json
import os
from collections import defaultdict

def load_results(filepath):
    """Load JSON results file."""
    with open(filepath, 'r') as f:
        return json.load(f)

def analyze_false_negatives(results):
    """Identify all false negative cases (VULNERABLE status = not detected)."""
    false_negatives = defaultdict(list)

    for test_id, result in results.get('detailed_results', {}).items():
        status = result.get('status', 'UNKNOWN')
        vuln_type = result.get('vulnerability_type', 'unknown')

        # VULNERABLE status means the detector scored 0/N (failed to detect)
        if status == 'VULNERABLE':
            false_negatives[vuln_type].append({
                'test_id': test_id,
                'score': result.get('score', 0),
                'max_score': result.get('max_score', 0),
                'language': result.get('language', 'unknown'),
                'vulnerabilities': result.get('vulnerabilities', [])
            })

    return dict(false_negatives)

def read_code_file(output_dir, test_id, language):
    """Read the generated code file."""
    extensions = {
        'python': '.py',
        'javascript': '.js',
        'typescript': '.ts',
        'php': '.php',
        'ruby': '.rb',
        'go': '.go',
        'java': '.java',
        'rust': '.rs',
        'csharp': '.cs',
        'cpp': '.cpp',
        'c': '.c'
    }

    ext = extensions.get(language, '.txt')
    filepath = os.path.join(output_dir, f"{test_id}{ext}")

    try:
        with open(filepath, 'r') as f:
            return f.read()
    except FileNotFoundError:
        return None

def analyze_missed_patterns(output_dir, false_negatives):
    """Analyze code to identify specific patterns being missed."""
    pattern_analysis = defaultdict(list)

    for vuln_type, cases in false_negatives.items():
        for case in cases[:5]:  # Analyze first 5 cases per type
            test_id = case['test_id']
            language = case['language']
            code = read_code_file(output_dir, test_id, language)

            if code:
                # Analyze the code to identify patterns
                analysis = {
                    'test_id': test_id,
                    'language': language,
                    'code_snippet': code[:500] + ('...' if len(code) > 500 else ''),
                    'code_length': len(code),
                    'vulnerabilities_found': case.get('vulnerabilities', [])
                }

                pattern_analysis[vuln_type].append(analysis)

    return dict(pattern_analysis)

def generate_improvement_recommendations(false_negatives, pattern_analysis):
    """Generate specific improvement recommendations based on analysis."""
    recommendations = {}

    # Priority ranking based on false negative count and severity
    priority_map = {
        'xss': ('CRITICAL', 'XSS has 80% false negative rate'),
        'command_injection': ('HIGH', 'Command injection has 69.6% false negative rate'),
        'path_traversal': ('HIGH', 'Path traversal has 68.4% false negative rate'),
        'hardcoded_secrets': ('HIGH', 'Secrets has 65.2% false negative rate'),
        'sql_injection': ('HIGH', 'SQL injection has 74.1% false negative rate'),
    }

    for vuln_type, cases in false_negatives.items():
        count = len(cases)
        if count == 0:
            continue

        priority, reason = priority_map.get(vuln_type, ('MEDIUM', f'{count} false negatives found'))

        # Get language breakdown
        languages = defaultdict(int)
        for case in cases:
            languages[case['language']] += 1

        recommendations[vuln_type] = {
            'priority': priority,
            'reason': reason,
            'false_negative_count': count,
            'affected_languages': dict(languages),
            'sample_cases': [case['test_id'] for case in cases[:3]],
            'patterns_to_add': []  # Will be filled based on specific analysis
        }

    return recommendations

def print_detailed_report(output_dir, results_file):
    """Generate detailed false negative analysis report."""
    print("=" * 80)
    print("DETAILED FALSE NEGATIVE ANALYSIS")
    print("=" * 80)
    print()

    # Load results
    results = load_results(results_file)

    # Analyze false negatives
    false_negatives = analyze_false_negatives(results)

    # Count totals
    total_fn = sum(len(cases) for cases in false_negatives.values())
    total_types = len(false_negatives)

    print(f"Total False Negatives: {total_fn}")
    print(f"Vulnerability Types Affected: {total_types}")
    print()

    # Analyze patterns
    pattern_analysis = analyze_missed_patterns(output_dir, false_negatives)

    # Generate recommendations
    recommendations = generate_improvement_recommendations(false_negatives, pattern_analysis)

    # Print by priority
    print("=" * 80)
    print("FALSE NEGATIVES BY PRIORITY")
    print("=" * 80)
    print()

    for priority in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']:
        priority_items = [(vt, rec) for vt, rec in recommendations.items() if rec['priority'] == priority]

        if not priority_items:
            continue

        print(f"\n{priority} Priority:")
        print("-" * 80)

        for vuln_type, rec in sorted(priority_items, key=lambda x: x[1]['false_negative_count'], reverse=True):
            print(f"\n{vuln_type.upper()}")
            print(f"  False Negatives: {rec['false_negative_count']}")
            print(f"  Reason: {rec['reason']}")
            print(f"  Affected Languages: {', '.join(f'{lang}({count})' for lang, count in rec['affected_languages'].items())}")
            print(f"  Sample Cases: {', '.join(rec['sample_cases'])}")

            # Show code samples if available
            if vuln_type in pattern_analysis and pattern_analysis[vuln_type]:
                print(f"\n  Sample Code Patterns (first case):")
                sample = pattern_analysis[vuln_type][0]
                print(f"    Test ID: {sample['test_id']}")
                print(f"    Language: {sample['language']}")
                print(f"    Code Length: {sample['code_length']} chars")
                if sample['vulnerabilities_found']:
                    print(f"    Partial Detections: {len(sample['vulnerabilities_found'])} issues found")
                else:
                    print(f"    Partial Detections: None (complete miss)")

    print()
    print("=" * 80)
    print("DETAILED PATTERN ANALYSIS")
    print("=" * 80)
    print()

    # Show top 5 vulnerability types with highest false negative rates
    top_5 = sorted(recommendations.items(), key=lambda x: x[1]['false_negative_count'], reverse=True)[:5]

    for vuln_type, rec in top_5:
        print(f"\n{vuln_type.upper()} - {rec['false_negative_count']} false negatives")
        print("-" * 80)

        if vuln_type in pattern_analysis:
            for i, analysis in enumerate(pattern_analysis[vuln_type][:3], 1):
                print(f"\nCase {i}: {analysis['test_id']} ({analysis['language']})")
                print(f"Code snippet:")
                print("```")
                print(analysis['code_snippet'])
                print("```")

                if analysis['vulnerabilities_found']:
                    print(f"\nPartial detections ({len(analysis['vulnerabilities_found'])}):")
                    for vuln in analysis['vulnerabilities_found'][:2]:
                        print(f"  - {vuln.get('type', 'UNKNOWN')}: {vuln.get('description', 'No description')[:100]}")
                else:
                    print("\nNo vulnerabilities detected (complete miss)")
                print()

if __name__ == "__main__":
    output_dir = "output/codellama"
    results_file = "reports/codellama_after_all_improvements.json"

    print_detailed_report(output_dir, results_file)
