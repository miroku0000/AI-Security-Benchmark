#!/usr/bin/env python3
"""
Test SQL Injection detector improvements on real generated files from various models.
"""
from tests.test_sql_injection import SQLInjectionDetector
import os

# Sample files to test from different models
test_files = [
    # Claude models (should be mostly SECURE)
    ("output/claude-opus-4-6_temp0.0/sql_001.py", "python", "Claude Opus 4.6 (temp=0.0)"),
    ("output/claude-sonnet-4-5/sql_002.js", "javascript", "Claude Sonnet 4.5"),
    ("output/claude-code/datastore_postgres_002.py", "python", "Claude Code (psycopg2.sql gold standard)"),

    # GPT models
    ("output/gpt-4o_temp0.0/sql_001.py", "python", "GPT-4o (temp=0.0)"),
    ("output/gpt-5.4_temp0.0/sql_002.js", "javascript", "GPT-5.4 (temp=0.0)"),

    # Deepseek models
    ("output/deepseek-coder_temp0.0/sql_001.py", "python", "DeepSeek Coder (temp=0.0)"),

    # Codex models
    ("output/codex-app-security-skill/sql_001.py", "python", "Codex App (Security Skill)"),
    ("output/codex-app-no-skill/sql_001.py", "python", "Codex App (No Skill)"),
]

detector = SQLInjectionDetector()

print("=" * 80)
print("Testing SQL Injection Detector on Real Generated Files")
print("=" * 80)

secure_count = 0
vulnerable_count = 0
unsupported_count = 0
not_found_count = 0

for file_path, language, model_name in test_files:
    print(f"\n{model_name}")
    print(f"File: {file_path}")
    print("-" * 80)

    if not os.path.exists(file_path):
        print("  ⚠ FILE NOT FOUND - SKIPPING")
        not_found_count += 1
        continue

    with open(file_path, 'r') as f:
        code = f.read()

    result = detector.analyze(code, language)
    score = result['score']
    max_score = result['max_score']

    print(f"  Score: {score}/{max_score}")

    # Determine primary vulnerability type
    if result['vulnerabilities']:
        primary_vuln = result['vulnerabilities'][0]
        vuln_type = primary_vuln['type']
        severity = primary_vuln['severity']
        description = primary_vuln['description'][:100]

        print(f"  Type: {vuln_type}")
        print(f"  Severity: {severity}")
        print(f"  Description: {description}...")

        if vuln_type == "SECURE":
            print("  ✓ SECURE")
            secure_count += 1
        elif vuln_type == "UNSUPPORTED":
            print("  ℹ UNSUPPORTED (refusal/documentation)")
            unsupported_count += 1
        elif vuln_type == "SQL_INJECTION":
            print("  ✗ VULNERABLE")
            vulnerable_count += 1
            # Show line number if available
            if 'line_number' in primary_vuln:
                print(f"  Line: {primary_vuln['line_number']}")

print("\n" + "=" * 80)
print("Summary")
print("=" * 80)
print(f"Total files tested: {len(test_files) - not_found_count}")
print(f"  ✓ SECURE: {secure_count}")
print(f"  ✗ VULNERABLE: {vulnerable_count}")
print(f"  ℹ UNSUPPORTED: {unsupported_count}")
print(f"  ⚠ NOT FOUND: {not_found_count}")
print("=" * 80)
