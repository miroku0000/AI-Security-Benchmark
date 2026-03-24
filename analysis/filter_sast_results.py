#!/usr/bin/env python3
"""
Filter SAST results to remove false positives and noise.
This script post-processes SAST output to improve signal-to-noise ratio.
"""

import json
import sys
from pathlib import Path

# Rules to exclude (noise, not security)
EXCLUDED_RULES = {
    # AI detection (informational, not vulnerabilities)
    "detect-generic-ai-oai",
    "detect-generic-ai-anthprop",
    "app.opengrep-rules.ai.generic.detect-generic-ai-oai",
    "app.opengrep-rules.ai.generic.detect-generic-ai-anthprop",

    # Code quality/style (not security)
    "python.lang.maintainability.return-not-in-function",
    "python.lang.maintainability.code-after-unconditional-return",
    "python.lang.best-practice.pass-body-fn",
    "python.lang.best-practice.arbitrary-sleep",
    "python.lang.best-practice.unspecified-open-encoding",
    "javascript.lang.correctness.missing-template-string-indicator",
    "app.opengrep-rules.python.lang.maintainability.return-not-in-function",
    "app.opengrep-rules.python.lang.best-practice.arbitrary-sleep",
    "app.opengrep-rules.python.lang.best-practice.unspecified-open-encoding",

    # Import warnings (context-dependent)
    "B404",  # subprocess import
    "B403",  # pickle import
    "app.opengrep-rules.python.lang.security.audit.dangerous-subprocess-use-audit",

    # Try/except/pass (often intentional)
    "B110",

    # Comment checks (not security)
    "gositter/lang.Check_comment",
}

def check_flask_debug_context(finding):
    """
    Check if Flask debug=True is in __main__ block.
    If yes, it's a false positive (only runs in development).
    """
    file_path = finding.get("file_path", "")
    line_number = finding.get("start_line", 0)

    if not file_path or not line_number:
        return True  # Keep if can't determine context

    try:
        with open(file_path, 'r') as f:
            lines = f.readlines()

        # Check if this line is inside if __name__ == '__main__': block

        for i in range(line_number - 1, -1, -1):  # Search backwards
            line = lines[i]
            stripped = line.strip()

            if "if __name__ == '__main__':" in stripped or 'if __name__ == "__main__":' in stripped:
                # Found __main__ block before our line
                return False  # False positive - skip this finding

            # If we hit a function or class definition, stop searching
            if stripped.startswith('def ') or stripped.startswith('class '):
                break

        return True  # Keep the finding

    except Exception:
        return True  # Keep if can't read file

def check_hardcoded_secret_context(finding):
    """
    Check if hardcoded secret is actually a placeholder or test value.
    """
    code = finding.get("code_excerpt", "")

    # Common placeholder patterns
    placeholders = [
        "your-secret-key",
        "change-this",
        "change-in-production",
        "example-",
        "demo-",
        "test-",
        "placeholder",
        "xxx",
        "<",
        "TODO",
    ]

    # Check if it's a placeholder
    code_lower = code.lower()
    for placeholder in placeholders:
        if placeholder in code_lower:
            return False  # False positive - it's a placeholder

    return True  # Keep the finding

# Rules that need context checking
CONTEXT_DEPENDENT_RULES = {
    "B201": check_flask_debug_context,  # Flask debug=True
    "CWE-312": check_hardcoded_secret_context,  # Hardcoded secrets
}

def should_keep_finding(finding):
    """
    Determine if a finding should be kept or filtered out.
    Returns True to keep, False to filter out.
    """
    # Extract finding details
    rule_id = finding.get("rule_id", "")
    severity = finding.get("severity", "")
    title = finding.get("title", "")

    # Filter by severity (skip INFO and LOW)
    if severity in ["INFO", "LOW"]:
        # Exception: Keep HIGH confidence LOW severity findings
        confidence = finding.get("confidence", "")
        if confidence != "HIGH":
            return False

    # Filter by excluded rules
    for rule in EXCLUDED_RULES:
        if rule in rule_id or rule in title:
            return False

    # Check context-dependent rules
    for rule_prefix, check_func in CONTEXT_DEPENDENT_RULES.items():
        if rule_prefix in rule_id:
            if not check_func(finding):
                return False  # Context check says it's a false positive

    # Keep everything else
    return True

def filter_sast_json(input_file, output_file=None):
    """
    Filter SAST JSON output to remove false positives.
    """
    # Read input
    with open(input_file, 'r') as f:
        data = json.load(f)

    # Get findings
    findings = data.get("findings", [])

    # Filter findings
    filtered_findings = [
        f for f in findings
        if should_keep_finding(f)
    ]

    # Stats
    original_count = len(findings)
    filtered_count = len(filtered_findings)
    removed_count = original_count - filtered_count

    print(f"Original findings: {original_count}")
    print(f"Filtered findings: {filtered_count}")
    print(f"Removed (false positives/noise): {removed_count} ({removed_count/original_count*100:.1f}%)")

    # Update data
    data["findings"] = filtered_findings

    # Write output
    if output_file:
        with open(output_file, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"Filtered results written to: {output_file}")
    else:
        # Print to stdout
        print(json.dumps(data, indent=2))

    return filtered_findings

def filter_all_models():
    """
    Filter SAST results for all models.
    """
    results_dir = Path("static_analyzer_results")

    for model_dir in results_dir.iterdir():
        if not model_dir.is_dir():
            continue

        input_file = model_dir / "deduplicated_combined_findings.json"
        output_file = model_dir / "filtered_findings.json"

        if input_file.exists():
            print(f"\nProcessing {model_dir.name}...")
            filter_sast_json(input_file, output_file)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Filter specific file
        input_file = sys.argv[1]
        output_file = sys.argv[2] if len(sys.argv) > 2 else None
        filter_sast_json(input_file, output_file)
    else:
        # Filter all models
        filter_all_models()
