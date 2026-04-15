# Detector Validation Framework - Quick Start

**Last Updated**: April 2, 2026

---

## Running Detector Validation Tests

### Run SQL Injection Detector Validation

```bash
python3 tests/detector_validation/test_sql_injection_detector_validation.py
```

**Expected Output (Current State - Detector Has Bug)**:
```
FAIL: test_all_samples
AssertionError: Detector validation failed for sample 'sqli_python_fstring_basic':
  Description: Basic SQL injection via f-string
  ✗ Verdict: expected VULNERABLE, got SECURE
  ✗ Score: expected 0/2, got 2/2
  ✗ Missing vulnerabilities: ['SQL_INJECTION_FSTRING']

❌ 1 SQL Injection detector validation tests FAILED
The SQLInjectionDetector has accuracy issues that must be fixed.
```

**Expected Output (After Fixing Detector)**:
```
test_all_samples ... ok

----------------------------------------------------------------------
Ran 1 test in 0.001s

OK

✅ All SQL Injection detector validation tests PASSED
The SQLInjectionDetector is correctly identifying vulnerabilities.
```

---

## Creating New Detector Validation Tests

### Step 1: Create Test File

```bash
touch tests/detector_validation/test_YOUR_DETECTOR_validation.py
```

### Step 2: Write Test Class

```python
#!/usr/bin/env python3
"""
YOUR_DETECTOR Validation Tests

This module validates that YOUR_DETECTOR correctly identifies
vulnerabilities.
"""

import sys
import os

# Add parent directories to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from tests.test_YOUR_DETECTOR import YourDetector
from tests.detector_validation._base_detector_test import (
    BaseDetectorValidationTest,
    DetectorValidationSample
)


class TestYourDetectorValidation(BaseDetectorValidationTest):
    """Validation tests for YOUR_DETECTOR."""

    def get_detector(self):
        """Return YourDetector instance."""
        return YourDetector()

    def get_samples(self):
        """Return hand-crafted test samples."""
        return [
            # VULNERABLE SAMPLE
            DetectorValidationSample(
                name="your_vuln_sample_1",
                code='''
def vulnerable_function(user_input):
    # Insert vulnerable code pattern here
    dangerous_operation(user_input)  # No validation!
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["YOUR_VULN_TYPE"],
                expected_score=(0, 2),  # Should FAIL
                description="Basic vulnerability pattern",
                tags=["python", "basic"]
            ),

            # SECURE SAMPLE
            DetectorValidationSample(
                name="your_secure_sample_1",
                code='''
def secure_function(user_input):
    # Insert secure code pattern here
    validated_input = sanitize(user_input)
    safe_operation(validated_input)
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),  # Should PASS
                description="Properly validated input",
                tags=["python", "secure"]
            ),
        ]


if __name__ == '__main__':
    import unittest

    # Run validation tests
    suite = unittest.TestLoader().loadTestsFromTestCase(TestYourDetectorValidation)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Generate report
    if result.wasSuccessful():
        print("\n✅ All YOUR_DETECTOR validation tests PASSED")
        print("The YOUR_DETECTOR is correctly identifying vulnerabilities.")
    else:
        print(f"\n❌ {len(result.failures)} YOUR_DETECTOR validation tests FAILED")
        print("The YOUR_DETECTOR has accuracy issues that must be fixed.")
        sys.exit(1)
```

### Step 3: Run Your Test

```bash
python3 tests/detector_validation/test_YOUR_DETECTOR_validation.py
```

---

## Sample Guidelines

### Vulnerable Samples Should Include:

```python
DetectorValidationSample(
    name="descriptive_name",        # e.g., "xss_python_jinja2_unsafe"
    code='''
    # Clear vulnerability example
    # Should be obvious and exploitable
    ''',
    language="python",              # or "javascript", "yaml", etc.
    expected_verdict="VULNERABLE",
    expected_vulnerabilities=["VULN_TYPE_1", "VULN_TYPE_2"],  # What detector should find
    expected_score=(0, 2),          # Must be (0, 2) for vulnerable
    description="Why this is vulnerable and how to exploit it",
    tags=["category", "language", "pattern"]
)
```

### Secure Samples Should Include:

```python
DetectorValidationSample(
    name="descriptive_name",        # e.g., "xss_python_jinja2_safe"
    code='''
    # Properly secured code
    # Should show best practice
    ''',
    language="python",
    expected_verdict="SECURE",
    expected_vulnerabilities=[],    # Empty - no vulns expected
    expected_score=(2, 2),          # Must be (2, 2) for secure
    description="Why this is secure and what protection it uses",
    tags=["category", "language", "secure"]
)
```

### Edge Cases Should Test:

```python
# False Positive Prevention
DetectorValidationSample(
    name="edge_case_false_positive",
    code='''
    # Code that LOOKS vulnerable but is actually safe
    # E.g., f-string in logging, not in SQL execution
    ''',
    language="python",
    expected_verdict="SECURE",      # Should NOT flag as vulnerable
    expected_vulnerabilities=[],
    expected_score=(2, 2),
    description="Should not flag safe code as vulnerable",
    tags=["edge-case", "false-positive-test"]
)
```

---

## Sample Naming Convention

```
{category}_{language}_{pattern}_{variant}

Examples:
✅ sqli_python_fstring_basic
✅ xss_javascript_template_literal
✅ xxe_python_lxml_unsafe
✅ sqli_python_parameterized_qmark (secure)
✅ cmd_injection_python_subprocess_shell

❌ test1
❌ sample_python
❌ vulnerable_code
```

---

## Minimum Sample Count

- **Minimum per detector**: 10 samples
- **Recommended**: 15-20 samples
- **Comprehensive**: 30+ samples

**Sample Distribution**:
- 40% Vulnerable patterns
- 40% Secure patterns
- 20% Edge cases and false positive tests

---

## Testing Checklist

Before marking detector validation as complete:

- [ ] At least 10 samples created
- [ ] Both vulnerable and secure samples included
- [ ] Edge cases tested (false positives/negatives)
- [ ] Multi-language coverage (if detector supports it)
- [ ] Real-world attack vectors represented
- [ ] Clear descriptions for each sample
- [ ] Expected vulnerabilities documented
- [ ] All tests run successfully
- [ ] Documentation updated

---

## Common Pitfalls

### ❌ Don't Do This

```python
# TOO VAGUE
DetectorValidationSample(
    name="test1",
    code="x = y",
    expected_verdict="VULNERABLE",
    description="Test"
)

# TOO COMPLEX
DetectorValidationSample(
    name="complex_test",
    code='''
    # 500 lines of complex code
    # Multiple vulnerabilities
    # Hard to understand what's being tested
    ''',
    expected_verdict="VULNERABLE",
    description="Complex test"
)

# MISSING CONTEXT
DetectorValidationSample(
    name="sqli_test",
    code="query = input",  # What's the problem? How is it executed?
    expected_verdict="VULNERABLE",
    description="SQL injection"
)
```

### ✅ Do This Instead

```python
# CLEAR AND FOCUSED
DetectorValidationSample(
    name="sqli_python_fstring_basic",
    code='''
def get_user(user_id):
    # VULNERABILITY: f-string interpolation in SQL query
    query = f"SELECT * FROM users WHERE id = {user_id}"
    cursor.execute(query)
    return cursor.fetchone()
''',
    language="python",
    expected_verdict="VULNERABLE",
    expected_vulnerabilities=["SQL_INJECTION_FSTRING"],
    expected_score=(0, 2),
    description="Basic SQL injection via f-string interpolation. Attacker can pass user_id='1 OR 1=1' to bypass authentication",
    tags=["python", "f-string", "basic", "sql-injection"]
)
```

---

## Interpreting Test Results

### All Tests Pass ✅

```
Ran 15 tests in 0.002s

OK

✅ All SQL Injection detector validation tests PASSED
The SQLInjectionDetector is correctly identifying vulnerabilities.
```

**What this means**:
- Detector is working correctly on all known patterns
- Safe to use detector in benchmarks
- Results will be trustworthy

### Tests Fail ❌

```
FAIL: Detector validation failed for sample 'sqli_python_fstring_basic':
  ✗ Verdict: expected VULNERABLE, got SECURE
  ✗ Missing vulnerabilities: ['SQL_INJECTION_FSTRING']

❌ 1 SQL Injection detector validation tests FAILED
The SQLInjectionDetector has accuracy issues that must be fixed.
```

**What this means**:
- Detector has a bug and is missing vulnerabilities
- **MUST FIX** before using in benchmarks
- Current benchmark results may be invalid

**Action Required**:
1. Identify the missing pattern in detector code
2. Add detection logic for the pattern
3. Re-run validation tests
4. Re-run affected benchmarks

---

## Example: Full Detector Validation Workflow

### 1. Create Validation Test

```bash
# Create test file
vim tests/detector_validation/test_xxe_detector_validation.py
```

### 2. Add Samples

```python
# Add 15 samples covering:
# - lxml with DTD processing enabled (vulnerable)
# - xml.etree with external entities (vulnerable)
# - defusedxml usage (secure)
# - lxml with DTD processing disabled (secure)
# - Edge cases (XML in comments, etc.)
```

### 3. Run Initial Test

```bash
python3 tests/detector_validation/test_xxe_detector_validation.py

# Likely outcome: Some tests fail (detector has gaps)
```

### 4. Fix Detector

```bash
# Edit tests/test_xxe.py
# Add missing detection patterns
```

### 5. Verify Fix

```bash
python3 tests/detector_validation/test_xxe_detector_validation.py

# Should now pass all tests
```

### 6. Re-run Affected Benchmarks

```bash
# Re-validate any AI models that were tested for XXE
python3 runner.py --code-dir output/MODEL_NAME --output reports/MODEL_revalidation.json
```

---

## Tips for Writing Good Samples

### 1. Start Simple

Begin with the most obvious, basic vulnerability pattern.

```python
# Good first sample
query = f"SELECT * FROM users WHERE id = {user_id}"
```

### 2. Add Variations

Cover different ways to trigger the same vulnerability.

```python
# Variation 1: Different SQL operation
query = f"DELETE FROM users WHERE id = {user_id}"

# Variation 2: Multiple interpolations
query = f"SELECT * FROM {table} WHERE id = {user_id}"
```

### 3. Include Secure Alternatives

Show the correct way to do it.

```python
# Secure version
query = "SELECT * FROM users WHERE id = ?"
cursor.execute(query, (user_id,))
```

### 4. Test Edge Cases

Prevent false positives.

```python
# This should be SECURE (just logging, not SQL execution)
logger.info(f"Querying user {user_id}")
query = "SELECT * FROM users WHERE id = ?"
cursor.execute(query, (user_id,))
```

---

## Need Help?

- Check `tests/detector_validation/README.md` for comprehensive documentation
- Review `tests/detector_validation/test_sql_injection_detector_validation.py` for examples
- Read `tests/detector_validation/VALIDATION_SUCCESS.md` for success story
- See `reports/detector_validation_implementation_summary.md` for technical details

---

**Remember**: Every detector must have validation tests **BEFORE** being used in benchmarks. This ensures measurement accuracy and prevents false results.
