#!/usr/bin/env python3
"""
Test the SQL Injection detector on actual generated files.
"""
from tests.test_sql_injection import SQLInjectionDetector

# Test on claude-code datastore_postgres_002.py (SECURE with psycopg2.sql)
with open('output/claude-code/datastore_postgres_002.py', 'r') as f:
    code = f.read()

print("Testing: output/claude-code/datastore_postgres_002.py")
print("=" * 60)
print("This file uses psycopg2.sql.SQL() and sql.Identifier() - GOLD STANDARD\n")

detector = SQLInjectionDetector()
result = detector.analyze(code, "python")

print(f"Score: {result['score']}/{result['max_score']}")
print(f"\nVulnerabilities found: {len(result['vulnerabilities'])}")

for i, vuln in enumerate(result['vulnerabilities'], 1):
    print(f"\n{i}. Type: {vuln['type']}")
    print(f"   Severity: {vuln['severity']}")
    print(f"   Description: {vuln['description'][:120]}...")
    if 'line_number' in vuln:
        print(f"   Line: {vuln['line_number']}")
    if 'code_snippet' in vuln:
        print(f"   Code: {vuln['code_snippet'][:80]}...")

print("\n" + "=" * 60)
if result['score'] == 2 and result['vulnerabilities'][0]['type'] == 'SECURE':
    print("✓ CORRECT - Recognized as SECURE (psycopg2.sql module)")
else:
    print("✗ INCORRECT - Should be SECURE with score 2/2")
