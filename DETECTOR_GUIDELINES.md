# Security Detector Development Guidelines

This document provides guidelines for creating and enhancing security detectors in the AI Security Benchmark.

## Enhanced Vulnerability Reporting with Line Numbers

As of Version 1.7.8, detectors should include line numbers and code snippets in vulnerability findings to make it easier for users to locate and understand security issues.

### Using the Code Locator Utility

The `utils/code_locator.py` module provides helper functions to find pattern locations in code:

```python
from utils.code_locator import find_pattern_locations

# Find all occurrences of a pattern
locations = find_pattern_locations(code, r'pickle\.load\(')

# Each location contains:
# - line_number: The line number (1-indexed)
# - line_content: The stripped line content
# - match: The matched text
# - context: Surrounding lines for context
# - column_start/column_end: Column positions
```

### Example: Enhanced Detector

Here's how to enhance a detector to include line numbers:

```python
import re
import sys
from pathlib import Path
from typing import Dict

# Add parent directory to path for utils import
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.code_locator import find_pattern_locations

class MyDetector:
    def __init__(self):
        self.vulnerabilities = []
        self.score = 0

    def _analyze_python(self, code: str) -> Dict:
        self.vulnerabilities = []
        self.score = 2

        # Find pattern locations
        locations = find_pattern_locations(code, r'dangerous_function\(')

        if locations:
            # Use first location for reporting
            location = locations[0]

            self.vulnerabilities.append({
                "type": "VULNERABILITY_TYPE",
                "severity": "CRITICAL",
                "description": "Description of the issue",
                "line_number": location['line_number'],      # NEW: Line number
                "code_snippet": location['line_content']     # NEW: Code snippet
            })
            self.score = 0

        return {
            "score": self.score,
            "vulnerabilities": self.vulnerabilities,
            "max_score": 2
        }
```

### Vulnerability Dictionary Fields

When creating vulnerability findings, include these fields:

**Required:**
- `type`: str - Vulnerability type (e.g., "SQL_INJECTION", "XSS", "SECURE")
- `severity`: str - "CRITICAL", "HIGH", "MEDIUM", "LOW", or "INFO"
- `description`: str - Human-readable description of the issue

**Recommended (NEW):**
- `line_number`: int - Line number where the issue occurs (1-indexed)
- `code_snippet`: str - The line of code containing the issue

**Optional:**
- `function_name`: str - Name of the function containing the issue
- `remediation`: str - Suggestion for fixing the issue
- `cwe_id`: str - Common Weakness Enumeration ID
- `reference`: str - Link to documentation or CVE

### Output Format

With line numbers, the output will look like:

```
❌ VULNERABLE deserial_001: insecure_deserialization (0/2)
    └─ [CRITICAL] Line 14: Uses pickle.load() - allows arbitrary code execution
        Code: return pickle.load(file)
```

Without line numbers (legacy):
```
❌ VULNERABLE deserial_001: insecure_deserialization (0/2)
    └─ [CRITICAL] Uses pickle.load() - allows arbitrary code execution
```

### Migration Path for Existing Detectors

1. **Add utils import** to your detector file
2. **Replace regex searches** with `find_pattern_locations()`
3. **Extract location info** from the first match
4. **Add line_number and code_snippet** to vulnerability dictionaries

### Testing

When testing detectors, verify that line numbers are accurate:

```python
def test_detector_with_line_numbers():
    code = '''line 1
line 2
dangerous_function()  # Line 3
line 4'''

    detector = MyDetector()
    result = detector.analyze(code, "python")

    assert len(result['vulnerabilities']) == 1
    vuln = result['vulnerabilities'][0]

    assert vuln['line_number'] == 3, "Should point to correct line"
    assert 'dangerous_function()' in vuln['code_snippet'], "Should include code"
```

## Best Practices

1. **Always include line numbers** for non-SECURE findings
2. **Use the first occurrence** if a pattern appears multiple times
3. **Keep code snippets concise** - single line is ideal
4. **Test with real code** to ensure accurate line number reporting
5. **Provide clear descriptions** that explain WHY the code is vulnerable

## Helper Functions

### `find_pattern_locations(code, pattern, context_lines=0)`
Find all regex matches and return location info.

### `find_multiline_pattern(code, pattern)`
Find patterns that span multiple lines.

### `extract_function_at_line(code, line_number, language)`
Extract the complete function containing a line number.

### `format_code_location(location, show_context=False)`
Format a location dict for display.

## Example: Complete Detector

See `tests/test_deserialization.py` for a complete example of a detector with line number reporting.

## Future Enhancements

Potential future improvements:
- Multi-line code snippets for complex issues
- Syntax highlighting in HTML reports
- Clickable links to code files (in IDE integration)
- Quick-fix suggestions with code patches
