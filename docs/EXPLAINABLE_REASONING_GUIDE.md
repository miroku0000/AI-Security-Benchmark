# Explainable Reasoning for Security Detectors

## Overview

This guide explains how to implement explainable reasoning in security detectors to enable automated and human analysis of false positives and false negatives.

## Why Explainable Reasoning?

**Problem**: When a detector flags code as vulnerable (or secure), analysts need to understand:
1. What facts/observations led to this conclusion?
2. What assumptions is the detector making?
3. What is the step-by-step logical reasoning?
4. What alternative explanations were considered?

**Solution**: Structured reasoning that makes all assumptions explicit.

## Key Principle: Separate Facts, Assumptions, and Logic

### Facts (Observations)
Things we can **definitively observe** in the code:
- ✅ "Line 42 contains: `{'$regex': f'@{domain}$'}`"
- ✅ "No `re.escape()` call found in entire file"
- ✅ "Variable `domain` is assigned from `request.args.get('domain')`"

### Assumptions
Things we **believe but could be wrong**:
- ⚠️ "Variable `domain` is user-controlled" → **Could be wrong if**: validated elsewhere
- ⚠️ "This regex is security-critical" → **Could be wrong if**: used in non-sensitive search
- ⚠️ "No validation exists" → **Could be wrong if**: validation in separate module

### Logic
How facts + assumptions → conclusion:
1. **Premise**: User input in $regex without escaping (Facts #1, #3, Assumption #1)
2. **Inference**: Attacker can inject regex metacharacters
3. **Conclusion**: Vulnerable to regex injection

## The "Could Be Wrong If" Clause

**This is the most important feature for identifying false positives.**

For every assumption, explicitly state when it could be incorrect:

```python
Assumption(
    description="The variable in the f-string is user-controlled",
    based_on=[observation_id_2],  # Observed: var = request.args.get()
    why_we_assume_this="Variable appears to come from request.args.get() which is user input",
    could_be_wrong_if=(
        "1. Variable is validated/sanitized elsewhere in code we didn't analyze, "
        "2. Variable comes from trusted source (database, config file), "
        "3. This is a test file/example code not used in production, "
        "4. Validation happens in middleware/decorator we didn't detect"
    ),
    confidence="high"  # high/medium/low based on evidence strength
)
```

## Example: NoSQL Regex Injection Detection

### Vulnerable Code
```python
domain = request.args.get('domain')
regex = f"@{domain}$"
users = db.users.find({"email": {"$regex": regex}})
```

### Structured Reasoning

#### Observations (Facts)
1. **[definite]** MongoDB $regex operator with f-string at line 2
   - Evidence: `f"@{domain}$"`

2. **[likely]** Variable `domain` comes from request parameters at line 1
   - Evidence: `domain = request.args.get('domain')`

3. **[definite]** No `re.escape()` call in entire file
   - Evidence: Searched `r're\.escape\('` - no matches

#### Assumptions (Beliefs that could be wrong)
1. **[high confidence]** Variable `domain` is user-controlled
   - Based on: Observation #2
   - Why: `request.args.get()` retrieves URL query parameters from user
   - **Could be wrong if**:
     - Domain is validated by middleware before reaching this code
     - This function is only called internally with trusted values
     - Input validation exists in separate module we didn't analyze

2. **[high confidence]** No sanitization happens before the regex
   - Based on: Observation #3
   - Why: No `re.escape()` detected in file
   - **Could be wrong if**:
     - Sanitization happens in helper function with different name
     - Variable is pre-sanitized before being passed to this function
     - Framework provides automatic sanitization we're unaware of

3. **[medium confidence]** This regex is used in security-critical context
   - Based on: Observation #1 (MongoDB query)
   - Why: Database queries often involve authentication/authorization
   - **Could be wrong if**:
     - This is a non-critical search where broad matches don't matter
     - Results are filtered by permissions layer after query
     - This is admin-only tool where regex injection is acceptable

#### Logical Chain
**Step 1**:
- Premise: User input embedded in $regex without escaping
- Based on: Observations #1, #2, #3 + Assumptions #1, #2
- Inference: Attacker can inject regex metacharacters (`.*`, `|`, `[]`, `^`, `$`)
- Confidence: high

**Step 2**:
- Premise: Regex metacharacters alter query matching logic
- Based on: Observation #1 (MongoDB $regex behavior)
- Inference: Attacker can match unintended documents
- Confidence: high

**Step 3**:
- Premise: Overly broad regex matches expose unauthorized data
- Based on: Assumption #3 (security-critical)
- Inference: Authentication bypass / data exfiltration possible
- Confidence: high

#### Conclusion
- **Verdict**: VULNERABLE
- **Type**: NOSQL_REGEX_INJECTION
- **Severity**: CRITICAL
- **Confidence**: high
- **Attack**: Input `domain='.*'` → regex `'@.*$'` matches ALL emails
- **Impact**: Authentication bypass, data exfiltration, timing attacks

#### Alternatives Considered
1. **Hypothesis**: "Maybe domain is validated elsewhere"
   - **Why rejected**: No validation function found (searched `validate_`, `sanitize_`, `isinstance`)
   - **⚠️ ALERT**: If validation exists in separate module/file, this is FALSE POSITIVE

2. **Hypothesis**: "Maybe this regex is not security-critical"
   - **Why rejected**: MongoDB queries typically involve user data access
   - **⚠️ ALERT**: Without full context, assumed security-critical. Could be FALSE POSITIVE if truly non-sensitive

## Using the Explainable Reasoning Module

### Import the module
```python
from utils.explainable_reasoning import (
    ExplainableReasoning,
    Observation,
    Assumption,
    LogicalStep,
    Conclusion,
    AlternativeExplanation
)
```

### Build reasoning step-by-step
```python
def detect_nosql_regex_injection(code: str) -> Dict:
    # 1. Create reasoning object
    reasoning = ExplainableReasoning()

    # 2. Add observations (facts you can prove)
    reasoning.observations.append(Observation(
        observation_id=1,
        observation_type="code_pattern",
        location="line 42",
        description="MongoDB $regex with f-string interpolation",
        evidence='{"$regex": f"@{domain}$"}',
        confidence="definite"
    ))

    # 3. Add assumptions (things you believe but could be wrong)
    reasoning.assumptions.append(Assumption(
        assumption_id=1,
        description="Variable is user-controlled",
        based_on=[1],  # Based on observation #1
        why_we_assume_this="Comes from request.args.get()",
        could_be_wrong_if="Validated elsewhere or from trusted source",
        confidence="high"
    ))

    # 4. Build logical chain
    reasoning.logical_chain.append(LogicalStep(
        step=1,
        premise="User input in regex without escaping",
        based_on_observations=[1],
        based_on_assumptions=[1],
        inference="Attacker can inject metacharacters",
        confidence="high"
    ))

    # 5. Draw conclusion
    reasoning.conclusion = Conclusion(
        verdict="VULNERABLE",
        vulnerability_type="NOSQL_REGEX_INJECTION",
        severity="CRITICAL",
        confidence="high",
        attack_scenario="Input '.*' matches ALL emails",
        impact="Authentication bypass, data exfiltration",
        missing_controls=["re.escape() sanitization"],
        recommendation="Use re.escape(domain) before regex"
    ))

    # 6. Document alternatives considered
    reasoning.alternatives_considered.append(AlternativeExplanation(
        hypothesis="Maybe validated elsewhere",
        why_considered="Common to validate at API boundary",
        why_rejected="No validation function found. Could be false positive if validation in separate module",
        based_on=[1]
    ))

    # 7. Convert to dict for JSON output (maintains backward compatibility)
    return {
        "type": "NOSQL_REGEX_INJECTION",
        "severity": "CRITICAL",
        "description": "...",
        "detection_reasoning": reasoning.to_dict()  # Includes both new and legacy formats
    }
```

## For Human Analysts: How to Use This

### Investigating a False Positive

1. **Check Assumptions First**
   - Look at each assumption's "could_be_wrong_if" field
   - Verify each assumption against the actual code
   - Common false positive causes:
     - ✗ "Variable is user-controlled" → Actually validated elsewhere
     - ✗ "No sanitization exists" → Sanitization in separate module
     - ✗ "Security-critical context" → Actually non-sensitive feature

2. **Verify Observations**
   - Check if observations are actually correct
   - Look at the evidence (line numbers, code snippets)
   - Sometimes patterns match incorrectly

3. **Review Logical Chain**
   - Does each step follow logically?
   - Are the inferences valid?
   - Check confidence levels

### Investigating a False Negative

1. **Check "Alternatives Considered"**
   - Did detector consider the actual vulnerability?
   - If not, what pattern did it miss?

2. **Check Observations**
   - What observations are missing?
   - What should have been detected but wasn't?

3. **Check Assumptions**
   - Did detector make wrong assumptions about security?
   - Example: Assumed validation exists when it doesn't

## For LLM Analyzers: Automated False Positive/Negative Detection

### Prompt Template for Analyzing False Positives

```
You are analyzing a security detector's reasoning for potential false positives.

CODE:
{actual_code}

DETECTOR REASONING:
{reasoning_json}

TASK: Verify each assumption and observation:

1. For each OBSERVATION, verify:
   - Is this observation actually true in the code?
   - Check line numbers and evidence

2. For each ASSUMPTION, verify:
   - Is this assumption correct?
   - Check the "could_be_wrong_if" scenarios
   - Does any scenario apply to this code?

3. For LOGICAL CHAIN, verify:
   - Does each inference follow from its premises?
   - Are confidence levels appropriate?

OUTPUT:
- If FALSE POSITIVE detected, explain which assumption/observation is wrong
- If TRUE POSITIVE confirmed, explain why reasoning is sound
```

### Prompt Template for Analyzing False Negatives

```
You are analyzing why a security detector missed a vulnerability.

CODE:
{vulnerable_code}

EXPECTED VULNERABILITY:
{expected_vuln_type}

DETECTOR REASONING:
{reasoning_json}

TASK: Identify what the detector missed:

1. What observations should have been made but weren't?
2. What patterns exist in the code that weren't detected?
3. Did detector make wrong assumptions about security?
4. Check "alternatives_considered" - was the actual vulnerability considered and rejected? Why?

OUTPUT:
- Explain what was missed
- Suggest what patterns detector should add to catch this
```

## Best Practices

### DO:
✅ Make every assumption explicit
✅ Include "could_be_wrong_if" for every assumption
✅ Use confidence levels realistically
✅ Document alternatives you considered
✅ Reference specific line numbers and code evidence
✅ Explain your logical reasoning step-by-step

### DON'T:
❌ Mix facts and assumptions together
❌ State assumptions as definite facts
❌ Skip the "could_be_wrong_if" field
❌ Use "definite" confidence when actually uncertain
❌ Forget to document why you rejected alternative explanations
❌ Omit evidence/line numbers from observations

## Migration Guide: Updating Existing Detectors

### Old Format (Legacy)
```python
{
    "detection_reasoning": {
        "patterns_checked": [...],
        "why_vulnerable": [...],  # Mixed facts + assumptions + reasoning
        "why_not_vulnerable": [],
        "evidence": {...}
    }
}
```

### New Format (Enhanced)
```python
{
    "detection_reasoning": {
        # New structured fields
        "observations": [...],  # Pure facts
        "assumptions": [...],  # Beliefs with "could_be_wrong_if"
        "logical_chain": [...],  # Step-by-step reasoning
        "conclusion": {...},
        "alternatives_considered": [...],

        # Legacy fields (auto-generated for compatibility)
        "patterns_checked": [...],
        "why_vulnerable": [...],
        "why_not_vulnerable": [...],
        "evidence": {...}
    }
}
```

The `ExplainableReasoning.to_dict()` method automatically generates legacy fields, so existing tooling continues to work.

## Example Integration in Detector

See `utils/explainable_reasoning.py` for the complete example in `build_reasoning_for_nosql_regex_injection()`.

## Summary

The key innovation is **making assumptions explicit with "could be wrong if" clauses**. This enables:

1. **Human analysts** to quickly check assumptions and identify false positives
2. **LLM analyzers** to automatically verify reasoning and find errors
3. **Detector developers** to understand their detection logic better
4. **Research** into detector accuracy and improvement

Every assumption is a potential source of false positives. By documenting them clearly, we enable efficient analysis and continuous improvement.
