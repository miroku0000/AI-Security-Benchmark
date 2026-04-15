# Explainable Reasoning System - Summary

## What We Built

A structured reasoning system for security detectors that makes all assumptions explicit to enable automated and human analysis of false positives/negatives.

## Core Innovation: "Could Be Wrong If" Clauses

Every assumption in detector reasoning now includes explicit scenarios where it might be incorrect:

```python
Assumption(
    description="Variable is user-controlled",
    could_be_wrong_if=(
        "1. Variable comes from trusted source (database, config), "
        "2. Validated elsewhere in separate module, "
        "3. Pre-sanitized before reaching this code"
    )
)
```

**Why this matters**:
- **Human analysts** can quickly check these scenarios to identify false positives
- **LLM analyzers** can automatically verify assumptions against actual code
- **Detector developers** can see their blind spots

## Structure

### 1. Observations (Facts)
Things we can definitively observe:
- Line 42: `{"$regex": f"@{domain}$"}`
- No `re.escape()` found in file
- Variable assigned from `request.args.get()`

### 2. Assumptions (Beliefs)
Things we believe but could be wrong:
- **Assumption**: "Variable is user-controlled"
  - **Confidence**: high
  - **Could be wrong if**: "Variable comes from trusted source or validated elsewhere"

### 3. Logical Chain
Step-by-step reasoning:
1. User input in regex without escaping → Can inject metacharacters
2. Metacharacters alter matching → Can match unintended documents
3. Unintended matches → Authentication bypass / data exfiltration

### 4. Conclusion
Final verdict with attack scenario, impact, and recommendation

### 5. Alternatives Considered
What else we considered and why we rejected it, with **FALSE POSITIVE ALERTS**:

```
⚠️ FALSE POSITIVE ALERT: If validation exists in separate module,
this could be FALSE POSITIVE. Check for:
- Middleware validation
- Decorator sanitization
- Calling code pre-validation
```

## Files Created

### 1. `/utils/explainable_reasoning.py`
Core module with data classes:
- `Observation` - Facts about code
- `Assumption` - Beliefs with "could be wrong if"
- `LogicalStep` - Reasoning chain
- `Conclusion` - Final verdict
- `AlternativeExplanation` - What else was considered
- `ExplainableReasoning` - Complete reasoning structure

**Key feature**: `to_dict()` generates both new structured format AND legacy format for backward compatibility.

### 2. `/docs/EXPLAINABLE_REASONING_GUIDE.md`
Complete guide covering:
- Why explainable reasoning matters
- How to separate facts, assumptions, and logic
- "Could be wrong if" clause best practices
- How human analysts use this
- How LLMs can automate false positive detection
- Prompt templates for LLM analyzers
- Migration guide from old format

### 3. `/docs/DETECTOR_RETROFIT_EXAMPLE.md`
Practical example showing:
- Before/after comparison
- Complete retrofitted detector code
- How assumptions become explicit
- FALSE POSITIVE ALERTS in alternatives
- Benefits for analysts
- Migration strategy (phase 1: high-value detectors first)

### 4. `/docs/EXPLAINABLE_REASONING_SUMMARY.md` (this file)
Executive summary and next steps

## Example: NoSQL Regex Injection

### Old Detection
```python
"why_vulnerable": [
    "User input embedded directly in regex pattern string",
    "No re.escape() found",
    "ATTACK: User sends .*"
]
```
**Problem**: Assumes variable is user input, but doesn't say this is an assumption or when it could be wrong.

### New Detection
```python
Observation(
    description="MongoDB $regex with f-string interpolation",
    evidence='{"$regex": f"@{domain}$"}',
    confidence="definite"  # This is a fact
)

Assumption(
    description="Variable is user-controlled",
    confidence="high",
    could_be_wrong_if=(
        "1. Variable comes from trusted source (database, config), "
        "2. Variable validated elsewhere (middleware, decorator), "
        "3. This is test/example code not used in production"
    )
)

AlternativeExplanation(
    hypothesis="Maybe variable is validated elsewhere",
    why_rejected=(
        "No validation function found. "
        "⚠️ FALSE POSITIVE ALERT: If validation in separate module, "
        "check for: middleware validation, decorator sanitization"
    )
)
```

**Benefit**: Analyst can immediately check: "Is there middleware validation?" → Find false positive in 30 seconds.

## Use Cases

### 1. Human Analyst: Investigating False Positive

**Workflow**:
1. Look at detector's assumptions
2. For each assumption, read "could_be_wrong_if"
3. Check code for those scenarios
4. Identify which scenario applies
5. **Root cause found in minutes instead of hours**

**Example**:
```
Assumption: "Variable is user-controlled"
Could be wrong if: "Variable comes from database"

→ Analyst checks: *looks at code*
→ Variable comes from db.config.get('domain')
→ FALSE POSITIVE identified! Variable is from database, not user.
```

### 2. LLM Analyzer: Automated False Positive Detection

**Prompt**:
```
Code: {actual_code}
Assumption: "Variable is user-controlled"
Could be wrong if: "Variable comes from database"

Task: Does variable actually come from database?
Check for: db.get(), config.get(), etc.
```

**LLM verifies**: Variable = `config.get('domain')` → Assumption violated → FALSE POSITIVE detected automatically.

### 3. Detector Developer: Understanding Detection Logic

**Before**: "Why did we flag this?"
**After**: Clear structure showing:
- What we observed (facts)
- What we assumed (beliefs)
- How we reasoned (logic)
- What we considered (alternatives)

Helps developers improve detectors by identifying weak assumptions.

## Key Benefits

### For Human Analysts
✅ **Fast false positive identification**: Check assumptions instead of debugging entire detector
✅ **Clear guidance**: "Could be wrong if" tells you exactly what to look for
✅ **Confidence levels**: Know which parts of reasoning are certain vs uncertain

### For LLM Analyzers
✅ **Verifiable reasoning**: Can check each assumption against actual code
✅ **Automated analysis**: Don't need to understand entire detection algorithm
✅ **Structured prompts**: Clear input format for LLM verification

### For Detector Developers
✅ **Explicit blind spots**: See what assumptions you're making
✅ **Improvement targets**: False positives often come from wrong assumptions
✅ **Better debugging**: Understand why detector flagged code

### For Research
✅ **Reproducible analysis**: Clear reasoning chain for papers
✅ **Comparative studies**: Compare detector assumptions across tools
✅ **Improvement metrics**: Track which assumptions cause most false positives

## Backward Compatibility

The `ExplainableReasoning.to_dict()` method generates both formats:

```python
{
    # New structured format
    "observations": [...],
    "assumptions": [...],
    "logical_chain": [...],
    "conclusion": {...},
    "alternatives_considered": [...],

    # Legacy format (auto-generated)
    "patterns_checked": [...],
    "why_vulnerable": [...],
    "why_not_vulnerable": [...],
    "evidence": {...}
}
```

**Result**: Existing tooling continues to work, new tooling gets enhanced reasoning.

## Next Steps for Rollout

### Phase 1: Retrofit High-Value Detectors
Start with detectors that have most false positives:
1. **NoSQL injection** - Example already created ✓
2. **Command injection** - Similar user input assumptions
3. **Path traversal** - Many "user-controlled path" assumptions
4. **IDOR** - "No ownership check" assumptions often wrong

### Phase 2: Create Helper Functions
Build reusable assumption patterns:
```python
def user_controlled_variable_assumption(var_name, evidence):
    """Standard assumption for user-controlled variables."""
    return Assumption(
        description=f"Variable '{var_name}' is user-controlled",
        could_be_wrong_if="Variable from database/config or validated elsewhere",
        ...
    )
```

### Phase 3: Automated Analysis
Build LLM-based tools to:
- Verify assumptions against actual code
- Identify false positives automatically
- Suggest detector improvements

### Phase 4: Feedback Loop
Use false positive analysis to:
- Identify common wrong assumptions
- Improve detector patterns
- Add better validation detection
- Reduce false positive rate

## Implementation Checklist

For each detector you retrofit:

- [ ] Import explainable reasoning module
- [ ] Identify what you're observing (facts)
- [ ] Identify what you're assuming (beliefs)
- [ ] Add "could be wrong if" for each assumption
- [ ] Build logical chain linking observations → conclusion
- [ ] Add alternatives considered with FALSE POSITIVE ALERTS
- [ ] Use `reasoning.to_dict()` for output
- [ ] Test with known false positive cases
- [ ] Verify assumptions correctly identified the false positive

## Example Test Case

```python
def test_false_positive_detection():
    """Test that assumptions correctly identify false positive."""

    # Code that's actually SECURE (domain from config)
    code = '''
domain = config.get('trusted_domain')  # From database config
regex = f"@{domain}$"
users = db.users.find({"email": {"$regex": regex}})
'''

    # Run detector
    detector = NoSQLInjectionDetector()
    result = detector.analyze(code)

    # Extract reasoning
    reasoning = result['vulnerabilities'][0]['detection_reasoning']

    # Check assumption
    assumption = reasoning['assumptions'][0]
    assert "user-controlled" in assumption['description']
    assert "database" in assumption['could_be_wrong_if']

    # Human analyst would check: Is variable from database?
    # In this case: YES → Assumption violated → FALSE POSITIVE identified
    print("✓ False positive detection works: assumption correctly identified issue")
```

## Success Metrics

Track these metrics after rollout:

### Quantitative
- **Time to identify false positive**: Should decrease from hours → minutes
- **False positive rate**: Should decrease as we improve assumptions
- **Automated detection rate**: % of false positives found by LLM without human
- **Assumption accuracy**: % of assumptions that are correct

### Qualitative
- **Analyst feedback**: "Much easier to debug false positives"
- **Developer feedback**: "Understand detector logic better"
- **Research value**: "Can explain detector behavior in papers"

## Documentation

Complete documentation in:
1. **EXPLAINABLE_REASONING_GUIDE.md** - Comprehensive guide with examples
2. **DETECTOR_RETROFIT_EXAMPLE.md** - Practical before/after example
3. **Code examples** in `utils/explainable_reasoning.py`
4. **Test cases** showing false positive detection

## Contact for Questions

See documentation files for:
- Detailed examples
- Best practices
- Common patterns
- Troubleshooting

## Summary

We've built a system that makes detector reasoning explicit and analyzable by:
1. Separating facts from assumptions
2. Adding "could be wrong if" to every assumption
3. Providing FALSE POSITIVE ALERTS for human analysts
4. Enabling automated LLM verification

**Key insight**: Most false positives come from wrong assumptions. By making assumptions explicit with clear "could be wrong if" clauses, we enable fast identification and continuous improvement.

**Next step**: Retrofit high-value detectors (NoSQL, command injection, path traversal, IDOR) following the example in DETECTOR_RETROFIT_EXAMPLE.md.
