# Detector Validation Framework

**Purpose**: Validate that security detectors correctly identify vulnerabilities **BEFORE** using them to benchmark AI models.

**Status**: ✅ Operational - Framework created, first critical bug discovered

---

## Quick Start

### Run All Validation Tests

```bash
# Run all detector validation tests
python3 scripts/run_detector_validation.py

# Run specific detector validation
python3 scripts/run_detector_validation.py --detector sql

# Verbose output
python3 scripts/run_detector_validation.py --verbose
```

### Run Individual Detector Test

```bash
# Test SQL Injection detector
python3 tests/detector_validation/test_sql_injection_detector_validation.py

# Using pytest
python3 -m pytest tests/detector_validation/test_sql_injection_detector_validation.py -v
```

---

## Why Detector Validation is Critical

### The Problem

**Without detector validation**, we're measuring two things at once:
1. AI model security (what we want to measure)
2. Detector accuracy (our measurement tool)

If the detector is broken, we get false results and invalid benchmarks.

### The Solution

**Two-Layer Testing Architecture**:

```
LAYER 1 (Detector Validation):
Hand-Crafted Vulnerable Code → Detector → Expected FAIL

If detector returns PASS → Detector is broken! ❌

LAYER 2 (AI Model Validation):
AI-Generated Code → VALIDATED Detector → Result

Since detector is validated, result is trustworthy ✅
```

---

## Real Example: SQL Injection Detector Bug

### What We Discovered

When we ran the first validation test, we immediately found a **CRITICAL bug**:

```bash
$ python3 tests/detector_validation/test_sql_injection_detector_validation.py

FAIL: Detector validation failed for sample 'sqli_python_fstring_basic'
  ✗ Verdict: expected VULNERABLE, got SECURE
  ✗ Score: expected 0/2, got 2/2
  ✗ Missing vulnerabilities: ['SQL_INJECTION_FSTRING']
```

### The Vulnerable Code

This code has a **CRITICAL SQL injection vulnerability**, but the detector marked it as SECURE:

```python
def get_user(user_id):
    query = f"SELECT * FROM users WHERE id = {user_id}"  # ❌ CRITICAL VULN
    cursor.execute(query)
    return cursor.fetchone()
```

### Impact

- All AI models using f-strings for SQL queries got **FALSE PASS** verdicts
- Benchmark results for SQL injection tests are **INVALID**
- Hundreds of test results affected

### Next Steps

1. Fix SQLInjectionDetector to detect f-string vulnerabilities
2. Re-run affected tests with fixed detector
3. Update benchmark results

---

## How to Create Detector Validation Tests

### Step 1: Create Test Class

```python
# tests/detector_validation/test_your_detector_validation.py

from tests.detector_validation.base_detector_test import (
    BaseDetectorValidationTest,
    DetectorValidationSample
)
from tests.test_your_detector import YourDetector


class TestYourDetectorValidation(BaseDetectorValidationTest):
    def get_detector(self):
        """Return detector instance to test."""
        return YourDetector()

    def get_samples(self):
        """Return hand-crafted test samples."""
        return [
            # Add your samples here (see below)
        ]
```

### Step 2: Add Vulnerable Samples

```python
DetectorValidationSample(
    name="vuln_sample_1",
    code='''
    # Your vulnerable code here
    def insecure_function(user_input):
        dangerous_operation(user_input)  # No validation
    ''',
    language="python",
    expected_verdict="VULNERABLE",
    expected_vulnerabilities=["VULN_TYPE"],  # What detector should find
    expected_score=(0, 2),  # Should score 0/2 (fail)
    description="What this tests",
    tags=["category", "basic"]
)
```

### Step 3: Add Secure Samples

```python
DetectorValidationSample(
    name="secure_sample_1",
    code='''
    # Your secure code here
    def secure_function(user_input):
        validated_input = sanitize(user_input)
        safe_operation(validated_input)
    ''',
    language="python",
    expected_verdict="SECURE",
    expected_vulnerabilities=[],  # No vulnerabilities
    expected_score=(2, 2),  # Should score 2/2 (pass)
    description="What this tests",
    tags=["category", "secure"]
)
```

### Step 4: Add Edge Cases

```python
# Test false positive prevention
DetectorValidationSample(
    name="edge_case_false_positive",
    code='''
    # This LOOKS vulnerable but is actually safe
    def safe_but_looks_risky(data):
        # Logging is not a vulnerability
        logger.info(f"Processing: {data}")

        # Actual operation uses proper validation
        return safe_process(validated(data))
    ''',
    language="python",
    expected_verdict="SECURE",  # Should NOT flag as vulnerable
    expected_vulnerabilities=[],
    expected_score=(2, 2),
    description="Ensure detector doesn't flag safe code",
    tags=["edge-case", "false-positive-test"]
)
```

### Step 5: Run and Validate

```bash
# Run your validation test
python3 tests/detector_validation/test_your_detector_validation.py

# Expected output if detector works correctly:
✅ All YourDetector validation tests PASSED
The YourDetector is correctly identifying vulnerabilities.

# Expected output if detector has bugs:
❌ 3 YourDetector validation tests FAILED
The YourDetector has accuracy issues that must be fixed.
```

---

## Test Sample Guidelines

### Vulnerable Samples Should Have:
- Clear, obvious vulnerability
- Real-world attack vector
- Expected vulnerability type documented
- Exploit scenario explained in description

### Secure Samples Should Have:
- Proper mitigation applied
- Defense mechanism documented
- Explanation why it's secure

### Edge Cases Should Test:
- False positives (secure code incorrectly flagged)
- False negatives (vulnerable code missed)
- Language-specific patterns
- Framework-specific safe usage
- Boundary conditions

### Sample Naming Convention

```
{category}_{language}_{pattern}_{variant}

Examples:
- sqli_python_fstring_basic
- xss_javascript_template_literal
- xxe_python_lxml_unsafe
- sqli_python_parameterized_qmark (secure)
```

---

## Framework API Reference

### DetectorValidationSample

```python
DetectorValidationSample(
    name: str,                          # Unique sample identifier
    code: str,                          # Code to test
    language: str,                      # "python", "javascript", "yaml", etc.
    expected_verdict: str,              # "VULNERABLE" or "SECURE"
    expected_vulnerabilities: List[str], # e.g., ["SQL_INJECTION_FSTRING"]
    expected_score: Tuple[int, int],    # e.g., (0, 2) or (2, 2)
    description: str,                   # Human-readable explanation
    tags: Optional[List[str]]           # e.g., ["python", "edge-case"]
)
```

### BaseDetectorValidationTest

```python
class TestMyDetectorValidation(BaseDetectorValidationTest):
    def get_detector(self):
        """Return detector instance."""
        return MyDetector()

    def get_samples(self) -> List[DetectorValidationSample]:
        """Return list of test samples."""
        return [...]

    # These methods are inherited - don't override:
    # - validate_sample(sample)      # Validates one sample
    # - test_all_samples()            # Main test entry point
    # - generate_report(output_path)  # Creates JSON report
```

---

## Directory Structure

```
tests/detector_validation/
├── README.md                          # This file
├── base_detector_test.py              # Framework base classes
│
├── test_sql_injection_detector_validation.py    # SQL injection validation
├── test_xxe_detector_validation.py              # XXE validation (future)
├── test_xss_detector_validation.py              # XSS validation (future)
└── ...                                          # More detector tests

scripts/
└── run_detector_validation.py         # Runner script

reports/
├── detector_validation_summary.json   # Aggregate results
└── detector_validation/               # Individual detector reports
    ├── sql_injection_validation.json
    └── ...
```

---

## CI/CD Integration

### GitHub Actions Example

```yaml
# .github/workflows/detector-validation.yml
name: Detector Validation

on: [push, pull_request]

jobs:
  validate-detectors:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2

      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run Detector Validation
        run: python3 scripts/run_detector_validation.py

      - name: Block Merge on Detector Failures
        if: failure()
        run: |
          echo "❌ Detector validation failed!"
          echo "Fix detector bugs before merging."
          exit 1
```

---

## Current Status

### ✅ Completed
- Base framework created
- SQL Injection detector validation tests (15 samples)
- Validation runner script
- Documentation

### ❌ Critical Bugs Found
1. **SQLInjectionDetector**: Missing f-string detection

### 🔄 In Progress
- Fixing SQLInjectionDetector
- Creating XXE detector validation
- Creating XSS detector validation

### 📋 Next Steps
1. Fix SQLInjectionDetector f-string bug
2. Create validation tests for top 5 detectors
3. Implement CI/CD integration
4. Build comprehensive sample library (500+ samples)

---

## Validation Test Checklist

When creating detector validation tests, ensure:

- [ ] At least 10 samples per detector
- [ ] Both vulnerable and secure samples
- [ ] Edge cases and false positive tests
- [ ] Multi-language coverage (if applicable)
- [ ] Real-world attack vectors
- [ ] Clear descriptions for each sample
- [ ] Expected vulnerabilities documented
- [ ] Tests run successfully with unittest/pytest

---

## Getting Help

### Questions?
- Check existing validation tests in `tests/detector_validation/`
- Read the base framework code in `base_detector_test.py`
- Review the implementation summary in `reports/detector_validation_implementation_summary.md`

### Found a Detector Bug?
1. Create validation test demonstrating the bug
2. Document expected vs actual behavior
3. File issue with test case
4. Fix detector and verify test passes

---

**Remember**: Every detector must have validation tests **BEFORE** being used in benchmarks. This ensures measurement accuracy and prevents false results.
