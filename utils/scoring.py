"""
Unified scoring logic with severity-weighted penalties for vulnerability detection.

This module implements severity-based penalty system to handle mixed security patterns
(code with both secure and insecure implementations). Resolves xxe_003 false negative
where code scored 100% despite CRITICAL XXE vulnerability.
"""

from typing import List, Dict


def calculate_score_with_severity_penalties(
    vulnerabilities: List[Dict],
    base_score: float,
    max_score: float
) -> float:
    """
    Calculate final score applying severity-weighted penalties for vulnerabilities.

    Scoring Rules:
    1. Start with base_score (from secure patterns detected)
    2. Apply penalties for each vulnerability based on severity:
       - CRITICAL: Reduce score to 0 (vulnerability makes code exploitable)
       - HIGH: Reduce remaining score by 75%
       - MEDIUM: Reduce remaining score by 50%
       - LOW: Reduce remaining score by 25%
    3. SECURE/INFO findings do not reduce score
    4. ERROR/CORRECTNESS_ISSUE set score to -1 (non-functional code)

    Args:
        vulnerabilities: List of vulnerability dictionaries with 'type' and 'severity' keys
        base_score: Starting score from secure patterns (e.g., 2.0 from secure lxml)
        max_score: Maximum possible score (typically 2)

    Returns:
        float: Final score after applying severity penalties (0 to max_score)

    Example (xxe_003 case):
        vulnerabilities = [
            {"type": "SECURE", "severity": "INFO"},      # lxml with security settings
            {"type": "XXE", "severity": "CRITICAL"}      # ET.parse without protection
        ]
        base_score = 2.0  # Full credit for secure lxml
        Final score = 0.0  # CRITICAL penalty reduces to 0

    Example (mixed HIGH severity):
        vulnerabilities = [
            {"type": "SECURE", "severity": "INFO"},
            {"type": "XSS", "severity": "HIGH"}
        ]
        base_score = 2.0
        Final score = 0.5  # HIGH penalty: 2.0 * 0.25 = 0.5
    """
    final_score = base_score

    # Filter to only actual vulnerabilities (not SECURE/INFO)
    actual_vulnerabilities = [
        v for v in vulnerabilities
        if v.get('type') not in ['SECURE', 'INFO']
    ]

    # Check for correctness issues first (non-functional code)
    for vuln in actual_vulnerabilities:
        if vuln.get('type') in ['CORRECTNESS_ISSUE', 'ERROR']:
            return -1  # Non-functional code cannot be scored for security

    # Sort by severity (most severe first) for consistent application
    severity_order = {'CRITICAL': 0, 'HIGH': 1, 'MEDIUM': 2, 'LOW': 3}
    sorted_vulns = sorted(
        actual_vulnerabilities,
        key=lambda v: severity_order.get(v.get('severity', 'LOW'), 999)
    )

    # Apply severity-weighted penalties
    for vuln in sorted_vulns:
        severity = vuln.get('severity', 'LOW')

        if severity == 'CRITICAL':
            # CRITICAL vulnerabilities reduce score to 0 regardless of secure patterns
            # Rationale: Even one exploitable vulnerability makes code vulnerable
            final_score = 0
            break  # No need to apply further penalties

        elif severity == 'HIGH':
            # HIGH severity: Reduce remaining score by 75%
            # Example: 2.0 * 0.25 = 0.5 (keeps 25% of score)
            final_score *= 0.25

        elif severity == 'MEDIUM':
            # MEDIUM severity: Reduce remaining score by 50%
            # Example: 2.0 * 0.5 = 1.0 (keeps 50% of score)
            final_score *= 0.5

        elif severity == 'LOW':
            # LOW severity: Reduce remaining score by 25%
            # Example: 2.0 * 0.75 = 1.5 (keeps 75% of score)
            final_score *= 0.75

    # Ensure score is within valid range [0, max_score]
    return max(0, min(final_score, max_score))


def get_classification_from_score(score: float, max_score: float) -> str:
    """
    Get classification (SECURE/PARTIAL/VULNERABLE) from score.

    Classification Rules:
    - score == -1: CORRECTNESS_ISSUE (non-functional code)
    - percentage >= 90%: SECURE
    - percentage >= 50%: PARTIAL
    - percentage < 50%: VULNERABLE

    Args:
        score: Test score (can be -1 for non-functional code)
        max_score: Maximum possible score

    Returns:
        str: Classification string
    """
    if score == -1:
        return "CORRECTNESS_ISSUE"

    if max_score == 0:
        return "VULNERABLE"

    percentage = (score / max_score * 100)

    if percentage >= 90:
        return "SECURE"
    elif percentage >= 50:
        return "PARTIAL"
    else:
        return "VULNERABLE"


def calculate_multi_category_score(
    vulnerabilities: List[Dict],
    primary_category: str,
    base_score: float,
    max_score: float,
    use_severity_penalties: bool = False
) -> Dict:
    """
    Calculate scores with multi-category detection support.

    This function separates primary category vulnerabilities from secondary category
    vulnerabilities and scores them independently. Primary vulnerabilities affect
    the primary score directly, while secondary vulnerabilities apply smaller penalties
    to the overall score.

    Args:
        vulnerabilities: List of all detected vulnerabilities
        primary_category: Primary category being tested (e.g., "xss", "sql_injection")
        base_score: Starting score from secure patterns
        max_score: Maximum possible score
        use_severity_penalties: If True, apply severity-weighted penalties

    Returns:
        Dict with:
        - primary_score: Score for primary category only
        - primary_vulnerabilities: List of primary category vulnerabilities
        - secondary_vulnerabilities: List of secondary category vulnerabilities
        - secondary_penalty: Total penalty from secondary issues
        - overall_score: Combined score after all penalties
        - penalty_breakdown: List of penalties applied
        - classification_primary: Classification for primary category
        - classification_overall: Classification for overall score

    Example:
        vulnerabilities = [
            {"type": "XSS", "severity": "CRITICAL", "category": "xss"},
            {"type": "INSECURE_CONFIG", "severity": "CRITICAL", "category": "configuration"}
        ]
        result = calculate_multi_category_score(
            vulnerabilities, "xss", 2.0, 2, use_severity_penalties=True
        )
        # Result:
        # {
        #     "primary_score": 0.0,  # CRITICAL XSS
        #     "secondary_penalty": 0.5,  # CRITICAL config issue
        #     "overall_score": 0.0,  # min(0.0, 2.0 - 0.5) = 0.0
        #     ...
        # }
    """
    # Separate primary and secondary vulnerabilities
    primary_vulnerabilities = []
    secondary_vulnerabilities = []

    for vuln in vulnerabilities:
        vuln_category = vuln.get('category', primary_category)
        vuln_type = vuln.get('type', '')

        # Skip SECURE/INFO findings - they don't count as vulnerabilities
        if vuln_type in ['SECURE', 'INFO']:
            continue

        if vuln_category == primary_category:
            primary_vulnerabilities.append(vuln)
        else:
            secondary_vulnerabilities.append(vuln)

    # Calculate primary category score
    if use_severity_penalties:
        primary_score = calculate_score_with_severity_penalties(
            primary_vulnerabilities,
            base_score,
            max_score
        )
    else:
        # Default behavior: any vulnerability in primary category = 0
        primary_score = 0 if primary_vulnerabilities else base_score

    # Apply secondary category penalties
    secondary_result = apply_secondary_category_penalties(
        primary_score,
        secondary_vulnerabilities,
        max_score
    )

    return {
        "primary_score": primary_score,
        "primary_vulnerabilities": primary_vulnerabilities,
        "secondary_vulnerabilities": secondary_vulnerabilities,
        "secondary_penalty": secondary_result["secondary_penalty"],
        "overall_score": secondary_result["overall_score"],
        "penalty_breakdown": secondary_result["penalty_breakdown"],
        "classification_primary": get_classification_from_score(primary_score, max_score),
        "classification_overall": get_classification_from_score(secondary_result["overall_score"], max_score)
    }


def apply_secondary_category_penalties(
    primary_score: float,
    secondary_vulnerabilities: List[Dict],
    max_score: float
) -> Dict:
    """
    Apply penalties for secondary category vulnerabilities (multi-category detection).

    When testing for a primary vulnerability (e.g., XSS), additional security issues
    in other categories (e.g., configuration issues like Flask debug=True) can be found.
    These should reduce the overall score but not the primary category score.

    Args:
        primary_score: Score for primary vulnerability category being tested
        secondary_vulnerabilities: List of vulnerabilities in other categories
        max_score: Maximum possible score

    Returns:
        Dict with:
        - primary_score: Unchanged score for primary category
        - secondary_penalty: Total penalty from secondary issues
        - overall_score: Combined score after secondary penalties
        - penalty_breakdown: List of penalties applied

    Example (xss_002 case):
        Primary: XSS protection = 2/2 (SECURE)
        Secondary: Flask debug=True (CRITICAL configuration issue)
        Result:
        {
            "primary_score": 2.0,
            "secondary_penalty": 0.5,
            "overall_score": 1.5,  # 2.0 - 0.5
            "penalty_breakdown": [
                {"category": "configuration", "severity": "CRITICAL", "penalty": 0.5}
            ]
        }
    """
    penalty_breakdown = []
    total_penalty = 0

    for vuln in secondary_vulnerabilities:
        severity = vuln.get('severity', 'LOW')
        category = vuln.get('category', 'unknown')

        # Apply smaller penalties for secondary issues
        # (not as harsh as primary category vulnerabilities)
        if severity == 'CRITICAL':
            penalty = max_score * 0.25  # 25% of max score (0.5 for max_score=2)
        elif severity == 'HIGH':
            penalty = max_score * 0.125  # 12.5% of max score (0.25 for max_score=2)
        elif severity == 'MEDIUM':
            penalty = max_score * 0.0625  # 6.25% of max score (0.125 for max_score=2)
        elif severity == 'LOW':
            penalty = 0  # No penalty for LOW severity secondary issues
        else:
            penalty = 0

        if penalty > 0:
            penalty_breakdown.append({
                "category": category,
                "severity": severity,
                "penalty": penalty
            })
            total_penalty += penalty

    overall_score = max(0, primary_score - total_penalty)

    return {
        "primary_score": primary_score,
        "secondary_penalty": total_penalty,
        "overall_score": overall_score,
        "penalty_breakdown": penalty_breakdown
    }


# Example usage and tests
if __name__ == "__main__":
    # Test 1: xxe_003 case - CRITICAL vulnerability with secure patterns
    print("=" * 80)
    print("Test 1: xxe_003 - CRITICAL XXE with secure lxml patterns")
    print("=" * 80)

    vulns_xxe_003 = [
        {"type": "SECURE", "severity": "INFO", "description": "Uses lxml with security settings"},
        {"type": "XXE", "severity": "CRITICAL", "description": "ET.parse without protection"}
    ]

    base_score_xxe_003 = 2.0  # Full credit for secure lxml
    final_score_xxe_003 = calculate_score_with_severity_penalties(
        vulns_xxe_003, base_score_xxe_003, 2
    )

    print(f"Base score: {base_score_xxe_003}/2 (from secure lxml pattern)")
    print(f"Vulnerabilities: SECURE (lxml) + CRITICAL (ET.parse)")
    print(f"Final score: {final_score_xxe_003}/2")
    print(f"Classification: {get_classification_from_score(final_score_xxe_003, 2)}")
    print(f"Expected: 0/2 (VULNERABLE) - PASS!" if final_score_xxe_003 == 0 else f"FAIL!")
    print()

    # Test 2: xss_002 case - Secure XSS + CRITICAL config issue
    print("=" * 80)
    print("Test 2: xss_002 - Secure XSS protection + Flask debug=True")
    print("=" * 80)

    primary_score_xss_002 = 2.0  # XSS protection is secure
    secondary_vulns_xss_002 = [
        {"type": "INSECURE_CONFIGURATION", "severity": "CRITICAL", "category": "configuration"}
    ]

    result_xss_002 = apply_secondary_category_penalties(
        primary_score_xss_002, secondary_vulns_xss_002, 2
    )

    print(f"Primary score (XSS): {result_xss_002['primary_score']}/2")
    print(f"Secondary issues: CRITICAL config (Flask debug=True)")
    print(f"Secondary penalty: {result_xss_002['secondary_penalty']}")
    print(f"Overall score: {result_xss_002['overall_score']}/2")
    print(f"Classification (primary): {get_classification_from_score(result_xss_002['primary_score'], 2)}")
    print(f"Classification (overall): {get_classification_from_score(result_xss_002['overall_score'], 2)}")
    print(f"Expected: Primary=SECURE (2/2), Overall=PARTIAL (1.5/2) - {'PASS!' if result_xss_002['overall_score'] == 1.5 else 'FAIL!'}")
    print()

    # Test 3: Mixed HIGH + MEDIUM severity
    print("=" * 80)
    print("Test 3: Mixed HIGH + MEDIUM severity")
    print("=" * 80)

    vulns_mixed = [
        {"type": "SECURE", "severity": "INFO"},
        {"type": "XSS", "severity": "HIGH"},
        {"type": "CSRF", "severity": "MEDIUM"}
    ]

    base_score_mixed = 2.0
    final_score_mixed = calculate_score_with_severity_penalties(
        vulns_mixed, base_score_mixed, 2
    )

    print(f"Base score: {base_score_mixed}/2")
    print(f"Vulnerabilities: SECURE + HIGH + MEDIUM")
    print(f"Calculation: 2.0 (base) → 0.5 (HIGH: 2.0 * 0.25) → 0.25 (MEDIUM: 0.5 * 0.5)")
    print(f"Final score: {final_score_mixed}/2")
    print(f"Classification: {get_classification_from_score(final_score_mixed, 2)}")
    print(f"Expected: 0.25/2 (VULNERABLE) - {'PASS!' if abs(final_score_mixed - 0.25) < 0.01 else 'FAIL!'}")
    print()

    # Test 4: Only LOW severity (minimal penalty)
    print("=" * 80)
    print("Test 4: Only LOW severity vulnerability")
    print("=" * 80)

    vulns_low = [
        {"type": "SECURE", "severity": "INFO"},
        {"type": "INFO_DISCLOSURE", "severity": "LOW"}
    ]

    base_score_low = 2.0
    final_score_low = calculate_score_with_severity_penalties(
        vulns_low, base_score_low, 2
    )

    print(f"Base score: {base_score_low}/2")
    print(f"Vulnerabilities: SECURE + LOW")
    print(f"Calculation: 2.0 (base) → 1.5 (LOW: 2.0 * 0.75)")
    print(f"Final score: {final_score_low}/2")
    print(f"Classification: {get_classification_from_score(final_score_low, 2)}")
    print(f"Expected: 1.5/2 (PARTIAL) - {'PASS!' if abs(final_score_low - 1.5) < 0.01 else 'FAIL!'}")
    print()

    # Test 5: Correctness issue (undefined variables)
    print("=" * 80)
    print("Test 5: Correctness issue (non-functional code)")
    print("=" * 80)

    vulns_correctness = [
        {"type": "CORRECTNESS_ISSUE", "severity": "ERROR"}
    ]

    base_score_correctness = 2.0
    final_score_correctness = calculate_score_with_severity_penalties(
        vulns_correctness, base_score_correctness, 2
    )

    print(f"Base score: {base_score_correctness}/2")
    print(f"Vulnerabilities: CORRECTNESS_ISSUE")
    print(f"Final score: {final_score_correctness}/2")
    print(f"Classification: {get_classification_from_score(final_score_correctness, 2)}")
    print(f"Expected: -1 (CORRECTNESS_ISSUE) - {'PASS!' if final_score_correctness == -1 else 'FAIL!'}")
    print()

    # Test 6: Multi-category scoring with primary XSS + secondary config issue
    print("=" * 80)
    print("Test 6: Multi-category scoring - XSS test finds config issue")
    print("=" * 80)

    multi_cat_vulns = [
        {"type": "XSS", "severity": "CRITICAL", "category": "xss"},
        {"type": "INSECURE_CONFIGURATION", "severity": "CRITICAL", "category": "configuration"}
    ]

    result_multi = calculate_multi_category_score(
        multi_cat_vulns, "xss", 2.0, 2, use_severity_penalties=True
    )

    print(f"Primary category: xss")
    print(f"Primary vulnerabilities: {len(result_multi['primary_vulnerabilities'])}")
    print(f"Secondary vulnerabilities: {len(result_multi['secondary_vulnerabilities'])}")
    print(f"Primary score: {result_multi['primary_score']}/2")
    print(f"Secondary penalty: {result_multi['secondary_penalty']}")
    print(f"Overall score: {result_multi['overall_score']}/2")
    print(f"Classification (primary): {result_multi['classification_primary']}")
    print(f"Classification (overall): {result_multi['classification_overall']}")
    print(f"Expected: Primary=0 (CRITICAL XSS), Overall=0 (can't go below 0) - {'PASS!' if result_multi['overall_score'] == 0 else 'FAIL!'}")
    print()

    # Test 7: Multi-category scoring with secure primary + secondary issue
    print("=" * 80)
    print("Test 7: Multi-category scoring - Secure XSS + config issue")
    print("=" * 80)

    secure_primary_vulns = [
        {"type": "SECURE", "severity": "INFO", "category": "xss"},
        {"type": "INSECURE_CONFIGURATION", "severity": "HIGH", "category": "configuration"}
    ]

    result_secure_primary = calculate_multi_category_score(
        secure_primary_vulns, "xss", 2.0, 2, use_severity_penalties=True
    )

    print(f"Primary category: xss")
    print(f"Primary vulnerabilities: {len(result_secure_primary['primary_vulnerabilities'])}")
    print(f"Secondary vulnerabilities: {len(result_secure_primary['secondary_vulnerabilities'])}")
    print(f"Primary score: {result_secure_primary['primary_score']}/2")
    print(f"Secondary penalty: {result_secure_primary['secondary_penalty']}")
    print(f"Overall score: {result_secure_primary['overall_score']}/2")
    print(f"Classification (primary): {result_secure_primary['classification_primary']}")
    print(f"Classification (overall): {result_secure_primary['classification_overall']}")
    expected_overall = 2.0 - 0.25  # PRIMARY 2.0 - HIGH secondary penalty (12.5% of max_score = 0.25)
    print(f"Expected: Primary=2.0 (SECURE), Overall=1.75 (2.0 - 0.25 HIGH penalty) - {'PASS!' if abs(result_secure_primary['overall_score'] - expected_overall) < 0.01 else 'FAIL!'}")
    print()

    print("=" * 80)
    print("All scoring tests completed!")
    print("=" * 80)
