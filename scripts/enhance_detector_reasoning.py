#!/usr/bin/env python3
"""
Script to automatically enhance detector reasoning with explainable format.

This script:
1. Scans detector files for vulnerability findings
2. Identifies which assumptions are being made (implicitly)
3. Adds explicit "could_be_wrong_if" clauses to make assumptions verifiable
4. Adds FALSE POSITIVE ALERT guidance for human analysts
"""

import re
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.reasoning_helpers import (
    user_controlled_variable_assumption,
    no_sanitization_assumption,
    security_critical_context_assumption,
    validation_elsewhere_alternative,
    trusted_source_alternative,
    non_critical_context_alternative
)


def analyze_vulnerability_pattern(vuln_dict: dict) -> dict:
    """
    Analyze a vulnerability dict and identify implicit assumptions.

    Returns dict with:
    - implicit_assumptions: List of assumptions being made
    - suggested_enhancements: Recommended additions to reasoning
    """
    description = vuln_dict.get('description', '').lower()
    why_vulnerable = vuln_dict.get('detection_reasoning', {}).get('why_vulnerable', [])
    why_vulnerable_str = ' '.join(why_vulnerable).lower()

    implicit_assumptions = []
    suggested_enhancements = []

    # Check for user-controlled variable assumption
    if any(keyword in description or keyword in why_vulnerable_str for keyword in [
        'user input', 'user-controlled', 'request.', 'req.params', 'req.body',
        'request.args', 'request.form', '$_GET', '$_POST'
    ]):
        implicit_assumptions.append({
            'type': 'user_controlled_variable',
            'description': 'Variable is user-controlled (comes from untrusted input)',
            'could_be_wrong_if': (
                'Variable comes from trusted source (database, config, hardcoded), '
                'validated elsewhere in separate module, pre-sanitized before this code'
            ),
            'false_positive_alert': (
                'Check for: (1) Validation in middleware/decorator, '
                '(2) Variable from database/config not user input, '
                '(3) Pre-sanitization in calling code'
            )
        })

    # Check for no sanitization assumption
    if any(keyword in description or keyword in why_vulnerable_str for keyword in [
        'no escaping', 'no sanitization', 'no validation', 'without escaping',
        'not found', 'missing'
    ]):
        implicit_assumptions.append({
            'type': 'no_sanitization',
            'description': 'No sanitization/escaping exists',
            'could_be_wrong_if': (
                'Sanitization in helper function with different name, '
                'framework provides automatic sanitization, '
                'validation in separate module not analyzed'
            ),
            'false_positive_alert': (
                'Check for: (1) Custom validation functions, '
                '(2) Framework-level sanitization, '
                '(3) Validation in parent class or separate file'
            )
        })

    # Check for security-critical context assumption
    if any(keyword in description or keyword in why_vulnerable_str for keyword in [
        'authentication', 'authorization', 'admin', 'sensitive', 'credentials',
        'password', 'security'
    ]):
        implicit_assumptions.append({
            'type': 'security_critical_context',
            'description': 'Operation is security-critical',
            'could_be_wrong_if': (
                'Non-critical feature where vulnerability acceptable risk, '
                'results filtered by permissions layer, '
                'admin-only tool with strict access controls'
            ),
            'false_positive_alert': (
                'Check for: (1) Is this actually sensitive data? '
                '(2) Are there downstream security controls? '
                '(3) Is this internal/admin-only?'
            )
        })

    # Generate suggested enhancements
    if implicit_assumptions:
        suggested_enhancements.append({
            'action': 'add_assumptions_section',
            'assumptions': implicit_assumptions
        })

        suggested_enhancements.append({
            'action': 'add_alternatives_considered',
            'alternatives': [
                {
                    'hypothesis': 'Maybe validation exists elsewhere',
                    'why_rejected': (
                        'No validation function found in this file. '
                        '⚠️ FALSE POSITIVE ALERT: If validation in separate module/middleware, '
                        'this could be FALSE POSITIVE. Check for middleware, decorators, '
                        'calling code pre-validation.'
                    )
                },
                {
                    'hypothesis': 'Maybe variable comes from trusted source',
                    'why_rejected': (
                        'Variable name/pattern suggests user input. '
                        '⚠️ FALSE POSITIVE ALERT: Could be false positive if variable from '
                        'database, config, or admin-controlled source. Trace variable origin.'
                    )
                }
            ]
        })

    return {
        'implicit_assumptions': implicit_assumptions,
        'suggested_enhancements': suggested_enhancements
    }


def enhance_existing_reasoning(detection_reasoning: dict) -> dict:
    """
    Enhance existing detection_reasoning dict with explicit assumptions.

    Keeps all existing fields, adds:
    - assumptions: List of explicit assumptions with "could_be_wrong_if"
    - alternatives_considered: Alternative explanations with FALSE POSITIVE ALERTS
    """
    enhanced = detection_reasoning.copy()

    # Add assumptions section if not present
    if 'assumptions' not in enhanced:
        # Analyze why_vulnerable to extract implicit assumptions
        why_vulnerable = enhanced.get('why_vulnerable', [])
        assumptions = []

        # Look for user input patterns
        for line in why_vulnerable:
            if any(keyword in line.lower() for keyword in ['user input', 'user-controlled', 'request', 'req.']):
                assumptions.append({
                    'description': 'Variable is user-controlled',
                    'confidence': 'high',
                    'could_be_wrong_if': (
                        'Variable from trusted source (database/config), '
                        'validated in middleware/decorator, '
                        'pre-sanitized before reaching this code'
                    )
                })
                break

        # Look for "no X found" patterns
        for line in why_vulnerable:
            if any(keyword in line.lower() for keyword in ['no', 'not found', 'missing', 'without']):
                assumptions.append({
                    'description': 'No sanitization/validation exists',
                    'confidence': 'high',
                    'could_be_wrong_if': (
                        'Sanitization in separate module/file, '
                        'framework automatic sanitization, '
                        'custom validation function with non-standard name'
                    )
                })
                break

        if assumptions:
            enhanced['assumptions'] = assumptions

    # Add alternatives_considered section if not present
    if 'alternatives_considered' not in enhanced:
        enhanced['alternatives_considered'] = [
            {
                'hypothesis': 'Maybe validation exists elsewhere before reaching this code',
                'why_considered': 'Common pattern: validate at API boundary, use safely downstream',
                'why_rejected': (
                    'No validation function found in this file. '
                    '\n⚠️ FALSE POSITIVE ALERT: This is the #1 cause of false positives. '
                    'If validation exists in separate module, middleware, decorator, or calling function, '
                    'this IS a FALSE POSITIVE.\n'
                    'Human analyst should check for:\n'
                    '- Middleware that validates/sanitizes all inputs\n'
                    '- Decorator on this function (@validate, @sanitize)\n'
                    '- Calling code that pre-validates\n'
                    '- Framework-level validation\n'
                    '- Validation in parent class methods'
                )
            },
            {
                'hypothesis': 'Maybe variable comes from trusted source, not user input',
                'why_considered': 'Variables can come from database, config, hardcoded constants',
                'why_rejected': (
                    'Variable name/usage pattern suggests dynamic user input. '
                    '\n⚠️ FALSE POSITIVE ALERT: Could be false positive if variable from:\n'
                    '- Database lookup (already-validated data)\n'
                    '- Configuration file (admin-controlled)\n'
                    '- Environment variable\n'
                    '- Hardcoded constant\n'
                    '- Admin-only parameter\n'
                    'Human analyst should: Trace variable origin in full codebase'
                )
            }
        ]

    return enhanced


def scan_detector_file(file_path: Path) -> dict:
    """
    Scan a detector file and analyze its vulnerability patterns.

    Returns:
    - total_vulnerabilities: Count of vulnerability findings
    - vulnerabilities_with_reasoning: Count that have detection_reasoning
    - vulnerabilities_needing_enhancement: Count that need explicit assumptions
    - examples: Sample vulnerability patterns found
    """
    content = file_path.read_text()

    # Count vulnerability additions
    vuln_appends = re.findall(r'self\.vulnerabilities\.append\(\{[^}]+\}', content, re.DOTALL)
    total_vulns = len(vuln_appends)

    # Count those with detection_reasoning
    vuln_with_reasoning = len(re.findall(r'"detection_reasoning":\s*\{', content))

    # Count those without explicit assumptions
    vuln_with_assumptions = len(re.findall(r'"assumptions":\s*\[', content))
    vuln_with_alternatives = len(re.findall(r'"alternatives_considered":\s*\[', content))

    needs_enhancement = vuln_with_reasoning - min(vuln_with_assumptions, vuln_with_alternatives)

    # Extract sample patterns
    examples = []
    vuln_types = re.findall(r'"type":\s*"([^"]+)"', content)
    examples = list(set(vuln_types))[:5]  # First 5 unique types

    return {
        'file': file_path.name,
        'total_vulnerabilities': total_vulns,
        'with_reasoning': vuln_with_reasoning,
        'with_assumptions': vuln_with_assumptions,
        'with_alternatives': vuln_with_alternatives,
        'needs_enhancement': max(0, needs_enhancement),
        'coverage': f"{vuln_with_reasoning}/{total_vulns}" if total_vulns > 0 else "0/0",
        'examples': examples
    }


def main():
    """Scan all detector files and report enhancement opportunities."""
    tests_dir = Path(__file__).parent.parent / 'tests'
    detector_files = sorted(tests_dir.glob('test_*.py'))

    print("=" * 80)
    print("DETECTOR REASONING ENHANCEMENT ANALYSIS")
    print("=" * 80)
    print()

    results = []
    for detector_file in detector_files:
        if detector_file.name in ['test_multi_language_support.py', '__init__.py']:
            continue

        try:
            result = scan_detector_file(detector_file)
            results.append(result)
        except Exception as e:
            print(f"Error analyzing {detector_file.name}: {e}")

    # Summary statistics
    total_detectors = len(results)
    total_vulns = sum(r['total_vulnerabilities'] for r in results)
    total_with_reasoning = sum(r['with_reasoning'] for r in results)
    total_with_assumptions = sum(r['with_assumptions'] for r in results)
    total_needs_enhancement = sum(r['needs_enhancement'] for r in results)

    print(f"Total detectors analyzed: {total_detectors}")
    print(f"Total vulnerability patterns: {total_vulns}")
    print(f"Patterns with detection_reasoning: {total_with_reasoning} ({100*total_with_reasoning/total_vulns if total_vulns > 0 else 0:.1f}%)")
    print(f"Patterns with explicit assumptions: {total_with_assumptions} ({100*total_with_assumptions/total_vulns if total_vulns > 0 else 0:.1f}%)")
    print(f"Patterns needing enhancement: {total_needs_enhancement}")
    print()

    # Priority list (most needing enhancement)
    print("PRIORITY LIST (Detectors needing most enhancement):")
    print("-" * 80)
    priority = sorted(results, key=lambda r: r['needs_enhancement'], reverse=True)[:15]

    for i, result in enumerate(priority, 1):
        print(f"{i:2d}. {result['file']:40s} - {result['needs_enhancement']:3d} patterns need enhancement")
        print(f"    Coverage: {result['coverage']:10s} | Examples: {', '.join(result['examples'][:3])}")

    print()
    print("=" * 80)
    print("RECOMMENDATION:")
    print("=" * 80)
    print()
    print("Use helper functions from utils/reasoning_helpers.py to enhance detectors:")
    print()
    print("from utils.reasoning_helpers import (")
    print("    user_controlled_variable_assumption,")
    print("    no_sanitization_assumption,")
    print("    validation_elsewhere_alternative")
    print(")")
    print()
    print("Then add to vulnerability dict:")
    print()
    print("vuln['detection_reasoning']['assumptions'] = [")
    print("    user_controlled_variable_assumption(1, 'var_name', obs_id, 'request.get()'),")
    print("    no_sanitization_assumption(2, 'SQL escaping', obs_id, ['parameterized queries'])")
    print("]")
    print()
    print("vuln['detection_reasoning']['alternatives_considered'] = [")
    print("    validation_elsewhere_alternative(1, 'input validation', obs_id),")
    print("    trusted_source_alternative(2, 'var_name', obs_id)")
    print("]")
    print()
    print("See docs/DETECTOR_RETROFIT_EXAMPLE.md for complete example.")


if __name__ == '__main__':
    main()
