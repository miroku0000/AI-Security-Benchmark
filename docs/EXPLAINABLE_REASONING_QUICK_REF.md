# Explainable Reasoning - Quick Reference

## TL;DR

Make detector assumptions explicit with "could be wrong if" clauses so analysts can quickly identify false positives.

## Core Components

### 1. Observation (Facts)
```python
Observation(
    observation_id=1,
    observation_type="code_pattern",  # or "data_flow", "security_control", "missing_pattern"
    location="line 42",
    description="What you observed",
    evidence="The actual code",
    confidence="definite"  # or "likely", "possible"
)
```

### 2. Assumption (Beliefs)
```python
Assumption(
    assumption_id=1,
    description="What you believe",
    based_on=[1, 2],  # Which observation IDs
    why_we_assume_this="Why you think this",
    could_be_wrong_if="How this could be incorrect",  # ← KEY FEATURE
    confidence="high"  # or "medium", "low"
)
```

### 3. Logical Step
```python
LogicalStep(
    step=1,
    premise="Logical premise",
    based_on_observations=[1, 2],
    based_on_assumptions=[1],
    inference="What you conclude",
    confidence="high"
)
```

### 4. Conclusion
```python
Conclusion(
    verdict="VULNERABLE",  # or "SECURE", "PARTIAL"
    vulnerability_type="NOSQL_REGEX_INJECTION",
    severity="CRITICAL",
    confidence="high",
    attack_scenario="How attacker exploits this",
    impact="What damage can be done",
    missing_controls=["What's missing"],
    present_controls=["What's there"],
    recommendation="How to fix"
)
```

### 5. Alternative Explanation
```python
AlternativeExplanation(
    hypothesis="What else you considered",
    why_considered="Why you thought about this",
    why_rejected="Why you ruled it out + ⚠️ FALSE POSITIVE ALERT",
    based_on=[1, 2]
)
```

## Usage Pattern

```python
from utils.explainable_reasoning import ExplainableReasoning

# 1. Create reasoning object
reasoning = ExplainableReasoning()

# 2. Add observations (facts)
reasoning.observations.append(Observation(...))

# 3. Add assumptions (beliefs with "could be wrong if")
reasoning.assumptions.append(Assumption(...))

# 4. Build logical chain
reasoning.logical_chain.append(LogicalStep(...))

# 5. Draw conclusion
reasoning.conclusion = Conclusion(...)

# 6. Document alternatives
reasoning.alternatives_considered.append(AlternativeExplanation(...))

# 7. Convert to dict (includes legacy format for compatibility)
return {
    "type": "VULNERABILITY_TYPE",
    "severity": "HIGH",
    "detection_reasoning": reasoning.to_dict()
}
```

## The "Could Be Wrong If" Template

Every assumption needs this field. Common patterns:

### User-Controlled Variable
```
could_be_wrong_if=(
    "1. Variable comes from trusted source (database, config), "
    "2. Variable validated elsewhere (middleware, decorator, calling code), "
    "3. Variable is pre-sanitized before reaching this code, "
    "4. This is test/example code not used in production"
)
```

### No Validation Exists
```
could_be_wrong_if=(
    "1. Validation in separate module/file we didn't analyze, "
    "2. Framework provides automatic validation, "
    "3. Validation in middleware/decorator not detected, "
    "4. Custom validation function with non-standard name"
)
```

### Security-Critical Context
```
could_be_wrong_if=(
    "1. This is non-sensitive search feature, "
    "2. Results filtered by permissions layer after query, "
    "3. Admin-only tool with strict access controls, "
    "4. Query only accesses public/non-sensitive data"
)
```

## FALSE POSITIVE ALERTS

In alternatives_considered, add explicit guidance for analysts:

```python
AlternativeExplanation(
    hypothesis="Maybe variable is validated elsewhere",
    why_rejected=(
        "No validation function found. "
        "\n⚠️ FALSE POSITIVE ALERT: If validation exists in separate module, "
        "this could be FALSE POSITIVE. Human analyst should check:\n"
        "- Middleware that validates all inputs\n"
        "- Decorator on this function that sanitizes parameters\n"
        "- Calling code that pre-validates\n"
        "- Framework-level validation we're unaware of"
    )
)
```

## Human Analyst Workflow

### Investigating False Positive
1. Read detector's assumptions
2. For each assumption, check "could_be_wrong_if"
3. Check actual code for those scenarios
4. Identify which scenario applies
5. Root cause found!

### Example
```
Assumption: "Variable is user-controlled"
Could be wrong if: "Variable from database"

Analyst checks code:
→ var = db.config.get('domain')
→ It IS from database!
→ FALSE POSITIVE identified in 30 seconds
```

## Confidence Levels

### Observations
- **definite**: 100% certain (direct pattern match)
- **likely**: >80% confident (strong evidence but not absolute)
- **possible**: >50% confident (weak evidence)

### Assumptions
- **high**: Strong evidence, likely correct
- **medium**: Reasonable belief, could be wrong
- **low**: Weak evidence, often wrong

### Use confidence levels to:
- Prioritize which assumptions to check first (low confidence = check first)
- Understand overall conclusion reliability

## Common Mistakes

### ❌ Don't
```python
# BAD: Stating assumption as fact
Observation(
    description="Variable is user-controlled",  # This is an assumption!
    confidence="definite"
)
```

### ✅ Do
```python
# GOOD: Clear it's an assumption
Observation(
    description="Variable appears to come from request parameters",
    confidence="likely"  # Not 100% certain
)

Assumption(
    description="Variable is user-controlled",
    could_be_wrong_if="Variable from database or validated elsewhere"
)
```

### ❌ Don't
```python
# BAD: Missing "could be wrong if"
Assumption(
    description="No validation exists",
    could_be_wrong_if=""  # EMPTY!
)
```

### ✅ Do
```python
# GOOD: Explicit scenarios
Assumption(
    description="No validation exists",
    could_be_wrong_if=(
        "Validation in separate module, "
        "framework automatic validation, "
        "middleware we didn't detect"
    )
)
```

## Backward Compatibility

The `reasoning.to_dict()` method generates both formats:

```python
{
    # New structured format
    "observations": [...],
    "assumptions": [...],
    "logical_chain": [...],

    # Legacy format (auto-generated)
    "patterns_checked": [...],
    "why_vulnerable": [...],
    "why_not_vulnerable": [...],
    "evidence": {...}
}
```

Existing tools keep working, new tools get enhanced data.

## Files to Read

1. **EXPLAINABLE_REASONING_GUIDE.md** - Complete guide
2. **DETECTOR_RETROFIT_EXAMPLE.md** - Before/after example
3. **EXPLAINABLE_REASONING_SUMMARY.md** - Overview
4. **utils/explainable_reasoning.py** - Implementation
5. **THIS FILE** - Quick reference

## One-Minute Example

```python
# Detect NoSQL regex injection
reasoning = ExplainableReasoning()

# Fact: Saw this pattern
reasoning.observations.append(Observation(
    observation_id=1,
    observation_type="code_pattern",
    location="line 5",
    description="MongoDB $regex with f-string",
    evidence='{"$regex": f"@{domain}$"}',
    confidence="definite"
))

# Belief: Variable is user input (but could be wrong!)
reasoning.assumptions.append(Assumption(
    assumption_id=1,
    description="Variable is user-controlled",
    based_on=[1],
    why_we_assume_this="F-string pattern suggests dynamic input",
    could_be_wrong_if="Variable from database/config or validated elsewhere",
    confidence="high"
))

# Logic: User input in regex → can inject metacharacters
reasoning.logical_chain.append(LogicalStep(
    step=1,
    premise="User input in $regex without escaping",
    based_on_observations=[1],
    based_on_assumptions=[1],
    inference="Attacker can inject .*|[]^$",
    confidence="high"
))

# Verdict: VULNERABLE
reasoning.conclusion = Conclusion(
    verdict="VULNERABLE",
    vulnerability_type="NOSQL_REGEX_INJECTION",
    severity="CRITICAL",
    confidence="high",
    attack_scenario="Input '.*' matches ALL emails",
    recommendation="Use re.escape(domain)"
)

# Alternative: Maybe validated elsewhere?
reasoning.alternatives_considered.append(AlternativeExplanation(
    hypothesis="Maybe validated elsewhere",
    why_rejected=(
        "No validation found. "
        "⚠️ Could be FALSE POSITIVE if validation in separate module"
    )
))

# Done! Now analyst can check assumption #1 to verify false positive
```

## Key Insight

**Most false positives come from wrong assumptions.**

By documenting assumptions with explicit "could be wrong if" clauses, analysts can verify each assumption in seconds instead of debugging the entire detector.

**Example success**:
- **Before**: False positive investigation takes 2+ hours
- **After**: Check 3 assumptions with "could be wrong if" → identify issue in 5 minutes

## Quick Checklist

When adding reasoning to a detector:

- [ ] Separate facts (observations) from beliefs (assumptions)
- [ ] Every assumption has "could_be_wrong_if"
- [ ] Confidence levels are realistic
- [ ] Logical chain links observations → conclusion
- [ ] Alternatives include FALSE POSITIVE ALERTS
- [ ] Test with known false positive case
- [ ] Verify assumptions correctly identify the false positive

## Need More Details?

- **Full guide**: EXPLAINABLE_REASONING_GUIDE.md
- **Retrofit example**: DETECTOR_RETROFIT_EXAMPLE.md
- **Implementation**: utils/explainable_reasoning.py
- **Summary**: EXPLAINABLE_REASONING_SUMMARY.md
