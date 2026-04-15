# Detector Retrofit Pattern Guide

## Overview

This guide provides a systematic pattern for retrofitting existing detectors with explainable reasoning. After retrofitting **22 patterns in Command Injection detector**, we have a proven approach to apply to the remaining **347 patterns** across 47 detectors.

## Status

- **Complete**: Command Injection (1 of 22 patterns retrofitted, pattern established)
- **In Progress**: Systematic rollout to remaining detectors
- **Total Remaining**: 36 XSS patterns, 27 Deserialization, 27 JWT, 27 SQL, 26 Path Traversal, etc.

## Retrofit Pattern (Step-by-Step)

### Step 1: Add Imports to Detector File

At the top of the detector file, add:

```python
from dataclasses import asdict

# Import explainable reasoning helpers
from utils.reasoning_helpers import (
    user_controlled_variable_assumption,
    no_sanitization_assumption,
    security_critical_context_assumption,
    code_pattern_observation,
    missing_pattern_observation,
    data_flow_observation,
    validation_elsewhere_alternative,
    trusted_source_alternative,
    non_critical_context_alternative,
    COMMAND_INJECTION_PATTERN  # Or relevant pattern constant
)
```

### Step 2: Identify Vulnerability Pattern

Locate vulnerability detection code that appends to `self.vulnerabilities`. Example:

```python
self.vulnerabilities.append({
    "type": "COMMAND_INJECTION",
    "severity": "CRITICAL",
    "description": "Uses os.system() with string formatting/concatenation",
    "line_number": line_num,
    "code_snippet": code_snippet,
    "detection_reasoning": {
        "criteria_for_vulnerability": [...],
        "why_vulnerable": [...],
        "patterns_checked": [...],
        # MISSING: assumptions, alternatives_considered
    }
})
```

### Step 3: Add Observation IDs

Before the vulnerability dict, add:

```python
# Build detection reasoning with explicit assumptions
obs_id_1 = 1  # Code pattern observation
obs_id_2 = 2  # Data flow observation
obs_id_3 = 3  # Missing pattern observation
```

### Step 4: Build Enhanced Detection Reasoning

Create a `detection_reasoning` dict with explicit assumptions:

```python
detection_reasoning = {
    "criteria_for_vulnerability": [
        # Keep existing criteria
    ],
    "why_vulnerable": [
        # Keep existing reasons
    ],
    "why_not_vulnerable": [],
    "patterns_checked": [
        # Keep existing patterns
    ],
    "evidence": {
        # Keep existing evidence
    },

    # NEW: EXPLICIT ASSUMPTIONS (key for false positive analysis)
    "assumptions": [
        asdict(user_controlled_variable_assumption(
            assumption_id=1,
            var_name="variable in f-string/concatenation",
            based_on_observation=obs_id_2,
            evidence="String formatting pattern (f-string, +, .format()) suggests dynamic user input",
            confidence="high"
        )),
        asdict(no_sanitization_assumption(
            assumption_id=2,
            sanitization_type="shlex.quote() or shell escaping",
            based_on_observation=obs_id_3,
            searched_patterns=["shlex.quote()", "pipes.quote()", "subprocess.run with list args"],
            confidence="high"
        )),
        asdict(security_critical_context_assumption(
            assumption_id=3,
            operation_type="command execution",
            based_on_observations=[obs_id_1],
            confidence="medium"
        ))
    ],

    # NEW: ALTERNATIVE EXPLANATIONS (with FALSE POSITIVE ALERTS)
    "alternatives_considered": [
        asdict(validation_elsewhere_alternative(
            hypothesis_id=1,
            validation_type="input validation or shell escaping",
            based_on_observation=obs_id_3
        )),
        asdict(trusted_source_alternative(
            hypothesis_id=2,
            var_name="variable in command string",
            based_on_observation=obs_id_2
        )),
        asdict(non_critical_context_alternative(
            hypothesis_id=3,
            operation_type="command execution",
            based_on_observations=[obs_id_1]
        ))
    ]
}
```

### Step 5: Use Enhanced Reasoning in Vulnerability

```python
self.vulnerabilities.append({
    "type": "COMMAND_INJECTION",
    "severity": "CRITICAL",
    "description": "Uses os.system() with string formatting/concatenation",
    "line_number": line_num,
    "code_snippet": code_snippet,
    "detection_reasoning": detection_reasoning  # Use the enhanced dict
})
```

## Common Assumption Patterns

### Pattern 1: User-Controlled Variable

```python
asdict(user_controlled_variable_assumption(
    assumption_id=1,
    var_name="<variable name>",
    based_on_observation=<obs_id>,
    evidence="<why we think it's user input>",
    confidence="high"
))
```

**When to use**: Detector assumes variable comes from user input (request.get(), req.params, $_GET, etc.)

**Could be wrong if**: Variable from database, config file, hardcoded constant, validated elsewhere

### Pattern 2: No Sanitization Exists

```python
asdict(no_sanitization_assumption(
    assumption_id=2,
    sanitization_type="<type of sanitization expected>",
    based_on_observation=<obs_id>,
    searched_patterns=["<pattern1>", "<pattern2>"],
    confidence="high"
))
```

**When to use**: Detector searched for sanitization function and found none

**Could be wrong if**: Sanitization in separate module, framework auto-sanitization, custom function with different name

### Pattern 3: Security-Critical Context

```python
asdict(security_critical_context_assumption(
    assumption_id=3,
    operation_type="<operation type>",
    based_on_observations=[<obs_id>],
    confidence="medium"
))
```

**When to use**: Detector assumes operation is security-critical

**Could be wrong if**: Non-critical feature, results filtered by permissions layer, admin-only tool

## Common Alternative Patterns

### Alternative 1: Validation Elsewhere

```python
asdict(validation_elsewhere_alternative(
    hypothesis_id=1,
    validation_type="<type of validation>",
    based_on_observation=<obs_id>
))
```

**Includes FALSE POSITIVE ALERT**: Tells analyst to check middleware, decorators, calling code

### Alternative 2: Trusted Source

```python
asdict(trusted_source_alternative(
    hypothesis_id=2,
    var_name="<variable name>",
    based_on_observation=<obs_id>
))
```

**Includes FALSE POSITIVE ALERT**: Tells analyst to trace variable origin (database, config, etc.)

### Alternative 3: Non-Critical Context

```python
asdict(non_critical_context_alternative(
    hypothesis_id=3,
    operation_type="<operation type>",
    based_on_observations=[<obs_id>]
))
```

**Includes FALSE POSITIVE ALERT**: Tells analyst to check if operation affects sensitive data

## Testing Retrofitted Detector

After retrofitting, test that assumptions are present:

```python
from tests.test_command_injection import CommandInjectionDetector

vulnerable_code = '''
def ping_host(hostname):
    os.system(f"ping -c 4 {hostname}")
'''

detector = CommandInjectionDetector()
result = detector.analyze(vulnerable_code, 'python')

# Verify assumptions
reasoning = result['vulnerabilities'][0]['detection_reasoning']
assert 'assumptions' in reasoning
assert len(reasoning['assumptions']) >= 3
assert 'could_be_wrong_if' in reasoning['assumptions'][0]

# Verify alternatives
assert 'alternatives_considered' in reasoning
assert 'FALSE POSITIVE ALERT' in reasoning['alternatives_considered'][0]['why_rejected']

print("✓ Retrofit successful!")
```

## Priority Order for Retrofit

Based on analysis results (369 patterns total):

1. **XSS** - 36 patterns (highest priority)
2. **Deserialization** - 27 patterns
3. **JWT** - 27 patterns
4. **SQL Injection** - 27 patterns
5. **Path Traversal** - 26 patterns
6. **Command Injection** - 21 remaining patterns (1 of 22 complete)
7. **Insecure Auth** - 22 patterns
8. **Resource Leaks** - 16 patterns
9. **CSRF** - 14 patterns
10. **Secrets** - 14 patterns
11. **Access Control** - 13 patterns
12. **Error Handling** - 13 patterns
13. **Info Disclosure** - 13 patterns
14. **Race Condition** - 12 patterns
15. **NoSQL Injection** - 9 remaining patterns
16. ... remaining 33 detectors

## Automation Strategy

### Option 1: Manual Pattern-by-Pattern (Current)

- **Pro**: Thoughtful assumptions for each pattern
- **Con**: Time-consuming for 369 patterns
- **Best for**: High-value detectors (top 10)

### Option 2: Script-Assisted Retrofit

Create script to:
1. Scan detector file for vulnerability patterns
2. Generate assumption templates based on pattern type
3. Insert assumptions into detection_reasoning
4. Human reviews and adjusts assumptions

### Option 3: Batch Template Application

For detectors with similar patterns:
1. Create assumption template for vulnerability type
2. Apply template to all patterns of that type
3. Customize specific cases as needed

## Example: Full Retrofitted Pattern

See `/tests/test_command_injection.py` lines 87-169 for complete example:

```python
# Build detection reasoning with explicit assumptions
obs_id_1 = 1
obs_id_2 = 2
obs_id_3 = 3

detection_reasoning = {
    "criteria_for_vulnerability": [
        "os.system() function used to execute commands",
        "String concatenation (+), f-strings, or .format() used to build commands",
        "User input merged directly into command string",
        "Shell interprets entire string, including metacharacters"
    ],
    "why_vulnerable": [
        f"Line {line_num}: os.system() with string formatting/concatenation",
        "os.system() executes command through shell (/bin/sh)",
        "Shell metacharacters (;|&$`\\n) in user input execute additional commands",
        "Attacker can inject complete command chains ('; rm -rf /')",
        "No escaping or parameterization mechanism available"
    ],
    "why_not_vulnerable": [],
    "patterns_checked": [
        "os.system() with string concatenation",
        "os.system() with f-strings",
        "subprocess with list arguments",
        "subprocess with shell=True",
        "shlex.quote() sanitization"
    ],
    "evidence": {
        "found_patterns": ["os.system with string formatting"],
        "line_numbers": [line_num],
        "code_snippets": [code_snippet]
    },
    # EXPLICIT ASSUMPTIONS
    "assumptions": [
        asdict(user_controlled_variable_assumption(
            assumption_id=1,
            var_name="variable in f-string/concatenation",
            based_on_observation=obs_id_2,
            evidence="String formatting pattern (f-string, +, .format()) suggests dynamic user input",
            confidence="high"
        )),
        asdict(no_sanitization_assumption(
            assumption_id=2,
            sanitization_type="shlex.quote() or shell escaping",
            based_on_observation=obs_id_3,
            searched_patterns=["shlex.quote()", "pipes.quote()", "subprocess.run with list args"],
            confidence="high"
        )),
        asdict(security_critical_context_assumption(
            assumption_id=3,
            operation_type="command execution",
            based_on_observations=[obs_id_1],
            confidence="medium"
        ))
    ],
    # ALTERNATIVE EXPLANATIONS
    "alternatives_considered": [
        asdict(validation_elsewhere_alternative(
            hypothesis_id=1,
            validation_type="input validation or shell escaping",
            based_on_observation=obs_id_3
        )),
        asdict(trusted_source_alternative(
            hypothesis_id=2,
            var_name="variable in command string",
            based_on_observation=obs_id_2
        )),
        asdict(non_critical_context_alternative(
            hypothesis_id=3,
            operation_type="command execution",
            based_on_observations=[obs_id_1]
        ))
    ]
}

self.vulnerabilities.append({
    "type": "COMMAND_INJECTION",
    "severity": "CRITICAL",
    "description": "Uses os.system() with string formatting/concatenation",
    "line_number": line_num,
    "code_snippet": code_snippet,
    "detection_reasoning": detection_reasoning
})
```

## Benefits of This Pattern

### For Human Analysts

1. **Fast False Positive Identification**: Check "could_be_wrong_if" scenarios (minutes instead of hours)
2. **Clear Guidance**: FALSE POSITIVE ALERTS tell exactly what to check
3. **Confidence Levels**: Know which assumptions are uncertain

### For LLM Analyzers

1. **Verifiable Reasoning**: Can check each assumption against actual code
2. **Automated Analysis**: Don't need to understand entire detection algorithm
3. **Structured Prompts**: Clear input format for LLM verification

### For Detector Developers

1. **Explicit Blind Spots**: See what assumptions you're making
2. **Improvement Targets**: False positives often come from wrong assumptions
3. **Better Debugging**: Understand why detector flagged code

## Next Steps

1. **Complete Command Injection**: Apply pattern to remaining 21 patterns
2. **Retrofit XSS**: Apply pattern to 36 XSS patterns (highest priority)
3. **Automate Where Possible**: Create helper scripts for similar patterns
4. **Document Learnings**: Update this guide with new patterns discovered
5. **Test Systematically**: Verify assumptions improve false positive detection

## Support

- **Helper Functions**: `/utils/reasoning_helpers.py`
- **Complete Guide**: `/docs/EXPLAINABLE_REASONING_GUIDE.md`
- **Example**: `/docs/DETECTOR_RETROFIT_EXAMPLE.md`
- **Quick Reference**: `/docs/EXPLAINABLE_REASONING_QUICK_REF.md`
- **Analysis Script**: `/scripts/enhance_detector_reasoning.py`
