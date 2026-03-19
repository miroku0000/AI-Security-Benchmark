#!/usr/bin/env python3
"""
Mistral-Only Verification Script

Uses only mistral for verification, which has proven to be the most accurate
of the local LLMs (96%+ accuracy vs 55% for llama3.1/deepseek-coder).

This script can verify individual test results or entire benchmark reports.
"""
import json
import subprocess
import argparse
from pathlib import Path
from datetime import datetime
from improved_verification_prompts import build_verification_prompt


def query_mistral(prompt, timeout=90):
    """Query mistral with the verification prompt"""
    try:
        result = subprocess.run(
            ['ollama', 'run', 'mistral'],
            input=prompt,
            capture_output=True,
            text=True,
            timeout=timeout
        )

        output = result.stdout.strip()
        if '{' in output:
            json_start = output.index('{')
            json_end = output.rindex('}') + 1
            json_str = output[json_start:json_end]
            return json.loads(json_str)
        else:
            return {
                "verdict": "error",
                "confidence": "low",
                "reasoning": "Could not parse LLM output"
            }
    except subprocess.TimeoutExpired:
        return {
            "verdict": "error",
            "confidence": "low",
            "reasoning": "Verification timeout"
        }
    except Exception as e:
        return {
            "verdict": "error",
            "confidence": "low",
            "reasoning": str(e)
        }


def verify_detection(code, language, original_prompt, detector_result, vulnerability_category):
    """
    Verify a single detection using mistral.

    Args:
        code: The generated code
        language: Programming language (python/javascript)
        original_prompt: Original prompt that generated the code
        detector_result: Dict with 'verdict' (SECURE/VULNERABLE) and 'vulnerabilities'
        vulnerability_category: Type of vulnerability (xss, idor, sql_injection, etc.)

    Returns:
        Dict with verification result
    """

    # Extract detector verdict and explanation
    detector_verdict = "VULNERABLE" if detector_result.get('score', 0) == 0 else "SECURE"

    # Build explanation from vulnerabilities
    # IMPORTANT: Only include findings relevant to the vulnerability category being tested
    # This prevents confusing mistral with unrelated issues
    vulnerabilities = detector_result.get('vulnerabilities', [])
    vuln_explanations = []

    # Map vulnerability categories to their primary keywords (must contain at least one)
    # and exclude keywords (must not contain any)
    category_filters = {
        'sql_injection': {
            'include': ['sql injection', 'parameterized', 'concatenation', 'sql query'],
            'exclude': []
        },
        'xss': {
            'include': ['xss', 'innerHTML', 'dangerouslySetInnerHTML', 'sanitiz', 'escape'],
            'exclude': []
        },
        'broken_access_control': {
            'include': ['access control', 'authorization', 'ownership', 'idor'],
            'exclude': []
        },
        'insecure_jwt': {
            'include': ['jwt', 'token', 'algorithm', 'signature'],
            'exclude': []
        },
        'command_injection': {
            'include': ['command injection', 'shell', 'exec', 'spawn'],
            'exclude': []
        },
        'path_traversal': {
            'include': ['path traversal', 'directory', '../'],
            'exclude': []
        },
        'insecure_auth': {
            'include': ['authentication', 'bcrypt', 'credential', 'session'],
            'exclude': []
        },
    }

    filter_config = category_filters.get(vulnerability_category, None)

    for vuln in vulnerabilities:
        vuln_type = vuln.get('type', 'UNKNOWN')
        desc = vuln.get('description', '').lower()

        # If no filter configured for this category, include all
        if not filter_config:
            vuln_explanations.append(f"[{vuln_type}] {vuln.get('description', '')}")
            continue

        # Check if description contains any include keywords
        include_match = any(kw in desc for kw in filter_config['include'])

        # Check if description contains any exclude keywords
        exclude_match = any(kw in desc for kw in filter_config['exclude'])

        # Include if matches include keywords and doesn't match exclude keywords
        if include_match and not exclude_match:
            vuln_explanations.append(f"[{vuln_type}] {vuln.get('description', '')}")

    detector_explanation = "\n".join(vuln_explanations) if vuln_explanations else "No findings reported"

    # Build verification prompt
    prompt = build_verification_prompt(
        code=code,
        language=language,
        original_prompt=original_prompt,
        detector_verdict=detector_verdict,
        detector_explanation=detector_explanation,
        vulnerability_category=vulnerability_category
    )

    # Get mistral's verdict
    result = query_mistral(prompt)

    # Normalize verdict - mistral sometimes returns variations
    verdict = result.get('verdict', 'error').lower()

    # The prompt asks: "Is the detector's assessment correct or false_positive?"
    # - "correct" means detector is right
    # - "false_positive" means detector wrongly flagged secure code as vulnerable
    # - mistral may also say "insecure"/"secure" to describe the code itself

    if verdict in ['correct', 'valid']:
        # Detector's assessment is correct (whatever it said)
        normalized_verdict = 'correct'
    elif verdict == 'false_positive':
        # Detector incorrectly flagged secure code
        normalized_verdict = 'false_positive'
    elif verdict == 'false_negative':
        # Detector missed a vulnerability
        normalized_verdict = 'false_negative'
    elif verdict in ['insecure', 'vulnerable', 'incorrect']:
        # Mistral saying code IS vulnerable
        # If detector said VULNERABLE → correct
        # If detector said SECURE → false negative
        if detector_verdict == 'VULNERABLE':
            normalized_verdict = 'correct'
        else:
            normalized_verdict = 'false_negative'
    elif verdict in ['secure', 'safe']:
        # Mistral saying code IS secure
        # If detector said SECURE → correct
        # If detector said VULNERABLE → false positive
        if detector_verdict == 'VULNERABLE':
            normalized_verdict = 'false_positive'
        else:
            normalized_verdict = 'correct'
    else:
        normalized_verdict = 'error'

    return {
        'llm': 'mistral',
        'verdict': normalized_verdict,
        'raw_verdict': result.get('verdict'),  # Keep original for debugging
        'confidence': result.get('confidence'),
        'reasoning': result.get('reasoning', ''),
        'detector_verdict': detector_verdict,
        'detector_explanation': detector_explanation
    }


def verify_benchmark_report(report_path, output_path=None, sample_size=None):
    """
    Verify an entire benchmark report using mistral.

    Args:
        report_path: Path to benchmark report JSON
        output_path: Where to save verification results (optional)
        sample_size: Only verify first N tests (for testing, optional)
    """

    print(f"\n{'='*80}")
    print("MISTRAL-ONLY VERIFICATION")
    print(f"{'='*80}")
    print(f"Report: {report_path}")
    print(f"Verifier: mistral (most accurate local LLM)")
    print(f"{'='*80}\n")

    # Load benchmark report
    with open(report_path) as f:
        report = json.load(f)

    model_name = report.get('model_name', 'Unknown')
    results = report.get('detailed_results', [])

    if sample_size:
        results = results[:sample_size]
        print(f"Testing with {sample_size} samples\n")

    verified_results = []
    stats = {
        'total': 0,
        'correct': 0,
        'false_positive': 0,
        'false_negative': 0,
        'error': 0
    }

    for i, result in enumerate(results, 1):
        test_id = result.get('prompt_id')
        category = result.get('category')
        language = result.get('language', 'python')
        original_prompt = result.get('prompt', '')
        score = result.get('score', 0)
        max_score = result.get('max_score', 2)

        # Read the generated code
        code_path = result.get('generated_code_path')
        if not code_path or not Path(code_path).exists():
            print(f"WARNING: {test_id}: Code file not found, skipping")
            continue

        with open(code_path) as f:
            code = f.read()

        # Determine detector status
        if score == max_score:
            detector_status = "SECURE"
        elif score == 0:
            detector_status = "VULNERABLE"
        else:
            detector_status = "PARTIAL"

        print(f"{i}/{len(results)} {test_id} ({category}): Detector={detector_status}", end=" ", flush=True)

        # Verify with mistral
        verification = verify_detection(
            code=code,
            language=language,
            original_prompt=original_prompt,
            detector_result=result,
            vulnerability_category=category
        )

        verdict = verification['verdict']
        confidence = verification['confidence']

        # Determine if verification agrees with detector
        # "correct" = detector is right
        # "false_positive" = detector flagged secure code as vulnerable
        if verdict == 'correct':
            verification_status = '[PASS] Correct'
            stats['correct'] += 1
        elif verdict == 'false_positive':
            verification_status = '[WARNING] False Positive'
            stats['false_positive'] += 1
        elif verdict == 'false_negative':
            verification_status = '[FAIL] False Negative'
            stats['false_negative'] += 1
        else:
            verification_status = '[ERROR] Error'
            stats['error'] += 1

        stats['total'] += 1

        print(f"→ {verification_status} ({confidence})")

        # Store result
        verified_results.append({
            'test_id': test_id,
            'model': model_name,
            'category': category,
            'detector_status': detector_status,
            'verification': verification
        })

    # Calculate accuracy
    accuracy = (stats['correct'] / stats['total'] * 100) if stats['total'] > 0 else 0

    print(f"\n{'='*80}")
    print("VERIFICATION SUMMARY")
    print(f"{'='*80}")
    print(f"Total verified:    {stats['total']}")
    print(f"[PASS] Correct:    {stats['correct']} ({stats['correct']/stats['total']*100:.1f}%)")
    print(f"[WARNING] False Positive: {stats['false_positive']} ({stats['false_positive']/stats['total']*100:.1f}%)")
    print(f"[FAIL] False Negative: {stats['false_negative']} ({stats['false_negative']/stats['total']*100:.1f}%)")
    print(f"[ERROR] Error:     {stats['error']}")
    print(f"\n{'='*80}")
    print(f"DETECTOR ACCURACY: {accuracy:.1f}%")
    print(f"{'='*80}\n")

    # Save results
    if output_path:
        verification_report = {
            'timestamp': datetime.now().isoformat(),
            'verifier': 'mistral',
            'source_report': str(report_path),
            'model_name': model_name,
            'statistics': stats,
            'accuracy': accuracy,
            'results': verified_results
        }

        with open(output_path, 'w') as f:
            json.dump(verification_report, f, indent=2)

        print(f"Verification report saved to: {output_path}\n")

    return verification_report


def main():
    parser = argparse.ArgumentParser(
        description='Verify benchmark results using mistral (most accurate local LLM)'
    )

    parser.add_argument(
        'report',
        help='Path to benchmark report JSON file'
    )

    parser.add_argument(
        '--output', '-o',
        help='Output path for verification results',
        default=None
    )

    parser.add_argument(
        '--sample', '-s',
        type=int,
        help='Only verify first N tests (for testing)',
        default=None
    )

    args = parser.parse_args()

    # Generate default output path if not specified
    if not args.output:
        report_path = Path(args.report)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        args.output = f"reports/mistral_verification_{report_path.stem}_{timestamp}.json"

    verify_benchmark_report(args.report, args.output, args.sample)


if __name__ == "__main__":
    main()
