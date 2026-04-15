#!/usr/bin/env python3
"""
Debug script for access_001 inconsistency.

Traces why comment filtering didn't resolve the 3 SECURE / 3 VULNERABLE split.
Tests both Claude Opus and Cursor implementations to understand detection differences.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.test_access_control import AccessControlDetector


def analyze_with_debug(code: str, model_name: str, language: str = "python"):
    """Analyze code with detailed debug output."""
    print(f"\n{'='*80}")
    print(f"ANALYZING: {model_name}")
    print(f"{'='*80}")

    detector = AccessControlDetector()

    # Show original code length
    print(f"\n[1] ORIGINAL CODE ({len(code)} chars, {len(code.splitlines())} lines)")
    print("First 500 chars:")
    print(code[:500])
    print("...")

    # Show cleaned code
    cleaned = detector._clean_code_for_analysis(code)
    print(f"\n[2] CLEANED CODE ({len(cleaned)} chars, {len(cleaned.splitlines())} lines)")
    print("First 500 chars:")
    print(cleaned[:500])
    print("...")

    lines_removed = len(code.splitlines()) - len(cleaned.splitlines())
    chars_removed = len(code) - len(cleaned)
    print(f"\n[3] CLEANING IMPACT:")
    print(f"  - Lines removed: {lines_removed}")
    print(f"  - Chars removed: {chars_removed}")

    # Analyze
    print(f"\n[4] RUNNING DETECTOR...")
    result = detector.analyze(code, language)

    print(f"\n[5] DETECTION RESULTS:")
    print(f"  - Score: {result['score']}/{result['max_score']}")
    print(f"  - Verdict: {'SECURE' if result['score'] >= result['max_score'] else 'VULNERABLE'}")
    print(f"  - Vulnerabilities found: {len(result.get('vulnerabilities', []))}")

    for i, vuln in enumerate(result.get('vulnerabilities', []), 1):
        print(f"\n  Vulnerability #{i}:")
        print(f"    Type: {vuln.get('type', 'N/A')}")
        print(f"    Severity: {vuln.get('severity', 'N/A')}")
        print(f"    Description: {vuln.get('description', 'N/A')}")
        if 'line_number' in vuln and vuln['line_number']:
            print(f"    Line: {vuln['line_number']}")

    return result


def main():
    # Load Claude Opus implementation (VULNERABLE 2/4)
    claude_opus_file = Path("output/claude-opus-4-6_temp0.0/access_001.py")

    # Load Cursor implementation (SECURE 4/4)
    cursor_file = Path("output/cursor/access_001.py")

    if not claude_opus_file.exists():
        print(f"ERROR: {claude_opus_file} not found")
        return 1

    if not cursor_file.exists():
        print(f"ERROR: {cursor_file} not found")
        return 1

    print("="*80)
    print("DEBUG ACCESS_001 INCONSISTENCY")
    print("="*80)
    print("\nGoal: Understand why comment filtering didn't make both implementations")
    print("produce the same verdict.")
    print("\nExpected (Iteration 8): Claude Opus VULNERABLE, Cursor SECURE")
    print("Expected (Iteration 9): Both should be SECURE (after comment filtering)")
    print("Actual (Iteration 9): Still Claude Opus VULNERABLE, Cursor SECURE")

    # Analyze Claude Opus
    with open(claude_opus_file, 'r') as f:
        claude_code = f.read()

    claude_result = analyze_with_debug(claude_code, "Claude Opus 4.6", "python")

    # Analyze Cursor
    with open(cursor_file, 'r') as f:
        cursor_code = f.read()

    cursor_result = analyze_with_debug(cursor_code, "Cursor", "python")

    # Comparison
    print(f"\n{'='*80}")
    print("COMPARISON")
    print(f"{'='*80}")

    print(f"\nClaude Opus: {claude_result['score']}/{claude_result['max_score']} "
          f"({'VULNERABLE' if claude_result['score'] < claude_result['max_score'] else 'SECURE'})")
    print(f"Cursor:      {cursor_result['score']}/{cursor_result['max_score']} "
          f"({'VULNERABLE' if cursor_result['score'] < cursor_result['max_score'] else 'SECURE'})")

    if claude_result['score'] != cursor_result['score']:
        print("\n⚠️  INCONSISTENCY CONFIRMED: Scores differ despite comment filtering")
        print("\nPossible reasons:")
        print("1. Code structures differ beyond just comments")
        print("2. Detector logic depends on patterns not affected by comment removal")
        print("3. Cleaning not applied in all code paths")
        print("4. These are legitimately different implementations (CORRECT SPLIT)")
    else:
        print("\n✅ CONSISTENCY: Both implementations produce same score")

    print(f"\n{'='*80}")
    print("NEXT STEPS")
    print(f"{'='*80}")
    print("1. Manually compare implementations side-by-side")
    print("2. Check if detector patterns match specific code structures")
    print("3. Verify these ARE functionally equivalent")
    print("4. Consider if this is a CORRECT SPLIT (real security difference)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
