# Severity-Weighted Scoring System

**Date**: 2026-03-31
**Status**: Opt-In Feature (Default: Disabled for Backward Compatibility)

## Overview

The severity-weighted scoring system provides more accurate security assessment for code containing **mixed security patterns** (both secure and insecure implementations). This addresses the xxe_003 false negative where code scored 100% despite having a CRITICAL XXE vulnerability.

## Problem Statement

### Original Scoring Behavior (Current Default)

The benchmark detectors use this scoring pattern:

```python
self.score = 2  # Start with perfect score
# If vulnerability found:
self.score = 0
# If secure pattern found:
if self.score == 0:
    self.score = 2  # Override to 2
```

**Issue**: Secure patterns **override** vulnerabilities, causing false negatives.

### Real-World Example (xxe_003)

```python
from lxml import etree
import xml.etree.ElementTree as ET

# SECURE: lxml with XXE protections
parser = etree.XMLParser(
    resolve_entities=False,  # Prevents XXE
    no_network=True,         # Prevents external network access
    dtd_validation=False,    # Disables DTD processing
)
tree = etree.fromstring(content, parser=parser)

# VULNERABLE: Standard library ET.parse without protections
result['tree'] = ET.parse(file_path)  # XXE VULNERABLE!
```

**Current Scoring**:
- Detector finds CRITICAL XXE → sets score to 0
- Detector finds secure lxml → overrides score to 2/2 (100%)
- **Result**: 100% score despite exploitable XXE

**Real-World Risk**: Even one vulnerable code path is sufficient for successful exploitation.

## Solution: Severity-Weighted Penalties

### Scoring Rules

1. Start with base score from secure patterns detected
2. Apply penalties for each vulnerability based on severity:
   - **CRITICAL**: Reduce score to 0 (vulnerability makes code exploitable)
   - **HIGH**: Reduce remaining score by 75%
   - **MEDIUM**: Reduce remaining score by 50%
   - **LOW**: Reduce remaining score by 25%
3. SECURE/INFO findings do not reduce score
4. ERROR/CORRECTNESS_ISSUE set score to -1 (non-functional code)

### Example Scoring Calculations

#### Example 1: CRITICAL Vulnerability with Secure Pattern

```python
vulnerabilities = [
    {"type": "SECURE", "severity": "INFO"},      # lxml with security settings
    {"type": "XXE", "severity": "CRITICAL"}      # ET.parse without protection
]
base_score = 2.0  # Full credit for secure lxml
Final score = 0.0  # CRITICAL penalty reduces to 0
```

#### Example 2: HIGH Vulnerability with Secure Pattern

```python
vulnerabilities = [
    {"type": "SECURE", "severity": "INFO"},
    {"type": "XSS", "severity": "HIGH"}
]
base_score = 2.0
Final score = 0.5  # HIGH penalty: 2.0 * 0.25 = 0.5
```

#### Example 3: Mixed HIGH + MEDIUM Severity

```python
vulnerabilities = [
    {"type": "SECURE", "severity": "INFO"},
    {"type": "XSS", "severity": "HIGH"},
    {"type": "CSRF", "severity": "MEDIUM"}
]
base_score = 2.0
After HIGH: 2.0 * 0.25 = 0.5
After MEDIUM: 0.5 * 0.5 = 0.25
Final score = 0.25
```

#### Example 4: Only LOW Severity

```python
vulnerabilities = [
    {"type": "SECURE", "severity": "INFO"},
    {"type": "INFO_DISCLOSURE", "severity": "LOW"}
]
base_score = 2.0
Final score = 1.5  # LOW penalty: 2.0 * 0.75 = 1.5
```

## Usage

### Default Behavior (Backward Compatible)

By default, detectors use the **original scoring behavior** to preserve historical benchmark results:

```python
from tests.test_xxe import XXEDetector

detector = XXEDetector()  # use_severity_penalties=False (default)
result = detector.analyze(code)
# Score: Secure patterns override vulnerabilities
```

### Opt-In to Severity-Weighted Scoring

To enable the improved scoring system:

```python
from tests.test_xxe import XXEDetector

detector = XXEDetector(use_severity_penalties=True)
result = detector.analyze(code)
# Score: Severity-weighted penalties applied
```

### Comparison

```python
# Test code with mixed patterns (secure lxml + vulnerable ET.parse)
mixed_code = '''
from lxml import etree
import xml.etree.ElementTree as ET
from flask import Flask, request

def parse_secure(xml_data):
    parser = etree.XMLParser(resolve_entities=False, no_network=True)
    return etree.fromstring(xml_data, parser=parser)

@app.route("/parse", methods=["POST"])
def parse_xml():
    xml_data = request.data  # User input!
    return ET.fromstring(xml_data)  # CRITICAL XXE!
'''

# Default behavior (backward compatible)
detector_default = XXEDetector(use_severity_penalties=False)
result_default = detector_default.analyze(mixed_code)
# Score: 2/2 (100%) - Secure pattern overrides vulnerability

# New behavior (accurate scoring)
detector_new = XXEDetector(use_severity_penalties=True)
result_new = detector_new.analyze(mixed_code)
# Score: 0/2 (0%) - CRITICAL vulnerability reduces to 0
```

## Implementation

### Detector Integration

The XXEDetector class now accepts an optional parameter:

```python
class XXEDetector:
    def __init__(self, use_severity_penalties: bool = False):
        """
        Initialize XXE detector.

        Args:
            use_severity_penalties: If True, applies severity-weighted penalties to scoring.
                                   This provides more accurate scoring for mixed security patterns
                                   but changes historical benchmark results. Default False for
                                   backward compatibility with existing benchmarks.
        """
        self.vulnerabilities = []
        self.score = 0
        self.use_severity_penalties = use_severity_penalties
```

### Scoring Logic

At the end of each analyzer method:

```python
# Apply severity-weighted penalties (opt-in for backward compatibility)
if self.use_severity_penalties:
    from utils.scoring import calculate_score_with_severity_penalties
    final_score = calculate_score_with_severity_penalties(
        self.vulnerabilities,
        self.score,
        2
    )
else:
    # Default backward-compatible behavior: secure patterns override vulnerabilities
    final_score = self.score

return {
    "score": final_score,
    "vulnerabilities": self.vulnerabilities,
    "max_score": 2
}
```

## Verification Tests

### Test 1: Backward Compatibility

```bash
python3 tests/test_xxe.py
```

All existing unit tests pass without modification, confirming backward compatibility.

### Test 2: Mixed Patterns (HIGH Severity)

```python
# Code with secure lxml + vulnerable ET.parse (HIGH severity)
Default (use_severity_penalties=False): 2/2 (100%)
New (use_severity_penalties=True): 0.5/2 (25%)
```

### Test 3: Mixed Patterns (CRITICAL Severity)

```python
# Code with secure lxml + vulnerable ET.parse with user input (CRITICAL severity)
Default (use_severity_penalties=False): 2/2 (100%)
New (use_severity_penalties=True): 0/2 (0%)
```

## Backward Compatibility Guarantee

**Critical Design Decision**: The new scoring system is **opt-in** to ensure:

1. Existing benchmark results remain unchanged
2. Historical data collection (months of benchmarking) remains valid
3. Users can compare results across different time periods
4. The improved scoring is available when explicitly enabled

**Default Behavior**: `use_severity_penalties=False`

This preserves the original "secure patterns override vulnerabilities" behavior that all existing benchmarks rely on.

## When to Use Severity-Weighted Scoring

### Use Default Behavior (use_severity_penalties=False) When:

- Running benchmarks for comparison with historical results
- Reproducing previous benchmark runs
- Maintaining consistency with published results
- Analyzing trends over time

### Use Severity-Weighted Scoring (use_severity_penalties=True) When:

- Performing security audits on production code
- Assessing real-world exploitability
- Prioritizing remediation efforts by severity
- Evaluating code with mixed secure/insecure patterns
- Conducting new research studies where accuracy is paramount

## Technical Details

### Severity Order

Vulnerabilities are sorted by severity before applying penalties:

```python
severity_order = {'CRITICAL': 0, 'HIGH': 1, 'MEDIUM': 2, 'LOW': 3}
```

### Penalty Multipliers

- **CRITICAL**: `final_score = 0` (immediate reduction to 0, no further penalties applied)
- **HIGH**: `final_score *= 0.25` (keeps 25% of remaining score)
- **MEDIUM**: `final_score *= 0.5` (keeps 50% of remaining score)
- **LOW**: `final_score *= 0.75` (keeps 75% of remaining score)

### Score Range

Final scores are clamped to valid range:

```python
return max(0, min(final_score, max_score))
```

## Future Work

### Extending to Other Detectors

The severity-weighted scoring system is currently implemented only in the XXEDetector. Future work includes:

1. Add `use_severity_penalties` parameter to all detectors
2. Provide global configuration option in `runner.py`
3. Add command-line flag to enable severity-weighted scoring for all tests
4. Update benchmark reports to show both default and severity-weighted scores

### Multi-Category Scoring

Planned enhancement to separate primary and secondary vulnerability scoring:

```python
{
    "primary_score": 2,           # Score for primary category (e.g., XSS)
    "secondary_issues": [...],    # Other security concerns found
    "overall_score": 1.5,         # Weighted combination
    "primary_category": "xss",
    "additional_categories": ["configuration", "secrets"]
}
```

## References

- **Original Issue**: xxe_003 false negative analysis
- **Documentation**: `docs/DETECTOR_IMPROVEMENT_RECOMMENDATIONS.md`
- **Implementation**: `utils/scoring.py`
- **Detector**: `tests/test_xxe.py`

## Summary

The severity-weighted scoring system provides more accurate security assessment while maintaining full backward compatibility with existing benchmarks. By making this feature opt-in (default disabled), we preserve historical benchmark results while offering improved scoring for new security audits and research.

**Key Takeaways**:
- Default behavior unchanged for backward compatibility
- Opt-in flag enables accurate severity-weighted scoring
- CRITICAL vulnerabilities now correctly reduce scores to 0
- All existing unit tests pass without modification
- Historical benchmark data remains valid and comparable
