# Detector Retrofit Example: Adding Explainable Reasoning

## Goal

Show how to enhance existing detectors with explainable reasoning **without** completely rewriting them.

## Before: Existing Detection Code

```python
# Pattern 4: NoSQL regex injection detection (current implementation)
regex_injection_pattern = r'\{\s*["\']?\$regex["\']?\s*:\s*f["\'].*\{.*\}'
has_regex_injection = re.search(regex_injection_pattern, code)
has_escape = re.search(r're\.escape\(', code)

if has_regex_injection and not has_escape and self.score == 2:
    self.vulnerabilities.append({
        "type": "NOSQL_REGEX_INJECTION",
        "severity": "CRITICAL",
        "description": "MongoDB $regex operator with unescaped user input...",
        "recommendation": "Use re.escape()...",
        "detection_reasoning": {
            "criteria_for_vulnerability": [
                "MongoDB $regex operator used in query",
                "User input embedded in regex pattern via f-string",
                "No re.escape() sanitization before regex use"
            ],
            "why_vulnerable": [
                "Found: {\"$regex\": f\"...{variable}...\"} pattern without re.escape()",
                "User input embedded directly in regex pattern string",
                "ATTACK: User sends regex metacharacters: .*, |, [], ^, $",
                "IMPACT: Authentication bypass - find any user without knowing full email"
            ],
            "why_not_vulnerable": [],
            "patterns_checked": [
                "MongoDB $regex operator usage",
                "F-string interpolation in regex patterns",
                "re.escape() sanitization function"
            ],
            "evidence": {
                "found_patterns": ["MongoDB $regex with f-string interpolation detected"],
                "line_numbers": [],
                "code_snippets": []
            }
        }
    })
    self.score = 0
```

### Problem with Current Approach
- Mixes facts and assumptions in "why_vulnerable"
- No explicit "this assumption could be wrong if..." statements
- Hard for humans/LLMs to identify which part of reasoning failed in false positives

## After: Enhanced with Explainable Reasoning

### Step 1: Import the helper
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

### Step 2: Build structured reasoning
```python
# Pattern 4: NoSQL regex injection detection (enhanced)
regex_injection_pattern = r'\{\s*["\']?\$regex["\']?\s*:\s*f["\'].*\{.*\}'
has_regex_injection = re.search(regex_injection_pattern, code)
has_escape = re.search(r're\.escape\(', code)

if has_regex_injection and not has_escape and self.score == 2:
    # Build explainable reasoning
    reasoning = ExplainableReasoning()

    # OBSERVATIONS (Facts we can prove)
    reasoning.observations.append(Observation(
        observation_id=1,
        observation_type="code_pattern",
        location=f"pattern match in code",  # Could extract actual line number
        description="MongoDB $regex operator used with f-string interpolation",
        evidence=has_regex_injection.group(0) if has_regex_injection else "{\"$regex\": f\"...{var}...\"}",
        confidence="definite"
    ))

    reasoning.observations.append(Observation(
        observation_id=2,
        observation_type="data_flow",
        location="code analysis",
        description="Variable in f-string likely comes from user input",
        evidence="Pattern suggests: variable = request.get(...); regex = f\"...{variable}...\"",
        confidence="likely"  # Not 100% certain without full data flow analysis
    ))

    reasoning.observations.append(Observation(
        observation_id=3,
        observation_type="missing_pattern",
        location="entire file",
        description="No re.escape() call found in code",
        evidence="Searched for r're\\.escape\\(' - no matches found",
        confidence="definite"
    ))

    # ASSUMPTIONS (What we believe but could be wrong about)
    reasoning.assumptions.append(Assumption(
        assumption_id=1,
        description="The variable in the f-string is user-controlled (comes from request/user input)",
        based_on=[2],
        why_we_assume_this=(
            "F-string pattern suggests dynamic input. MongoDB queries in web apps typically "
            "use request parameters. Variable name/pattern suggests user input."
        ),
        could_be_wrong_if=(
            "1. Variable comes from trusted source (database, config file, hardcoded constant), "
            "2. Variable is validated/sanitized before this code (in middleware, decorator, or calling function), "
            "3. This is test/example code not used in production, "
            "4. Variable is an admin-only parameter with access controls"
        ),
        confidence="high"
    ))

    reasoning.assumptions.append(Assumption(
        assumption_id=2,
        description="re.escape() is not called elsewhere before this regex is used",
        based_on=[3],
        why_we_assume_this=(
            "Searched entire file for re.escape() and found no matches. "
            "Typically sanitization happens near usage."
        ),
        could_be_wrong_if=(
            "1. Escaping happens in helper function with different name (sanitize_regex, clean_input), "
            "2. Variable is pre-sanitized in calling code before being passed to this function, "
            "3. Framework/library provides automatic escaping we're unaware of, "
            "4. Validation exists in separate module/file not analyzed"
        ),
        confidence="high"
    ))

    reasoning.assumptions.append(Assumption(
        assumption_id=3,
        description="This regex is used in security-critical context (authentication, authorization, data access)",
        based_on=[1],
        why_we_assume_this=(
            "MongoDB queries in web applications are typically used for database lookups "
            "which often involve authentication, authorization, or sensitive data access. "
            "$regex with user input pattern suggests search/filter functionality."
        ),
        could_be_wrong_if=(
            "1. This is a non-critical search feature where overly broad matches don't pose security risk, "
            "2. Results are filtered by permissions layer after query returns, "
            "3. This is admin-only tool where regex injection is acceptable risk, "
            "4. Query is for non-sensitive data (public articles, tags, categories)"
        ),
        confidence="medium"  # Less certain - depends on context we don't have
    ))

    # LOGICAL CHAIN (Step-by-step reasoning)
    reasoning.logical_chain.append(LogicalStep(
        step=1,
        premise="User-controlled input is embedded in MongoDB $regex pattern without escaping",
        based_on_observations=[1, 2, 3],
        based_on_assumptions=[1, 2],
        inference="Attacker can inject regex metacharacters (.*|[]^$) into the pattern",
        confidence="high"
    ))

    reasoning.logical_chain.append(LogicalStep(
        step=2,
        premise="Regex metacharacters alter MongoDB query matching behavior",
        based_on_observations=[1],
        based_on_assumptions=[],  # This is a fact about MongoDB behavior
        inference="Attacker can make regex match broader set of documents than intended",
        confidence="high"
    ))

    reasoning.logical_chain.append(LogicalStep(
        step=3,
        premise="Overly broad regex matches can expose data user shouldn't access",
        based_on_observations=[],
        based_on_assumptions=[3],  # Depends on security-critical context assumption
        inference="Authentication bypass, authorization bypass, or data exfiltration becomes possible",
        confidence="high"  # High IF assumption #3 is correct
    ))

    # CONCLUSION
    reasoning.conclusion = Conclusion(
        verdict="VULNERABLE",
        vulnerability_type="NOSQL_REGEX_INJECTION",
        severity="CRITICAL",
        confidence="high",
        attack_scenario=(
            "Attacker provides input containing regex metacharacters. "
            "Example: If code expects domain='example.com', attacker sends domain='.*' → "
            "regex becomes '@.*$' which matches ALL emails instead of specific domain. "
            "In authentication context: attacker can match any user email without knowing exact address."
        ),
        impact=(
            "1. Authentication bypass: Match any user account without full credentials, "
            "2. Authorization bypass: Access documents outside intended scope, "
            "3. Data exfiltration: Timing attacks to extract data character-by-character, "
            "4. Database enumeration: Use regex wildcards to discover data patterns"
        ),
        missing_controls=[
            "re.escape() to sanitize regex metacharacters from user input",
            "Input validation to reject regex special characters",
            "Exact string matching instead of regex where possible"
        ],
        present_controls=[],
        recommendation=(
            "ALWAYS use re.escape() to sanitize user input before embedding in regex:\n"
            "  import re\n"
            "  safe_domain = re.escape(domain)\n"
            "  regex_pattern = f\"@{safe_domain}$\"\n"
            "  users = db.users.find({\"email\": {\"$regex\": regex_pattern}})\n\n"
            "This escapes all regex metacharacters so '.*' becomes literal '\\.\*'"
        )
    )

    # ALTERNATIVES CONSIDERED
    reasoning.alternatives_considered.append(AlternativeExplanation(
        hypothesis="Maybe the variable is validated elsewhere before reaching this code",
        why_considered="Common pattern: validate at API boundary, then use safely downstream",
        why_rejected=(
            "No validation function found in code (searched for: validate_, sanitize_, check_, "
            "verify_, isinstance, type checking). No re.escape() detected. "
            "\n⚠️ FALSE POSITIVE ALERT: If validation exists in separate module/file, "
            "middleware, decorator, or calling function that we didn't analyze, this could be "
            "a FALSE POSITIVE. Human analyst should check for:\n"
            "- Middleware that validates all inputs\n"
            "- Decorator on this function that sanitizes parameters\n"
            "- Calling code that pre-validates before calling this function\n"
            "- Framework-level validation we're unaware of"
        ),
        based_on=[3]  # Based on observation that no validation found
    ))

    reasoning.alternatives_considered.append(AlternativeExplanation(
        hypothesis="Maybe this regex is not used in security-critical context",
        why_considered=(
            "Some regex searches are for non-sensitive data where broad matches "
            "don't pose security risk (e.g., public article search)"
        ),
        why_rejected=(
            "MongoDB queries in web applications typically involve user data access. "
            "Even if not authentication, overly broad matches could leak data. "
            "\n⚠️ FALSE POSITIVE ALERT: Without full application context, we assume "
            "security-critical. This could be FALSE POSITIVE if:\n"
            "- Query is for public/non-sensitive data only\n"
            "- Results are filtered by permissions layer after query\n"
            "- This is admin-only tool where regex injection is acceptable\n"
            "Human analyst should check: What data does this query access? "
            "Who can access this endpoint?"
        ),
        based_on=[]
    ))

    reasoning.alternatives_considered.append(AlternativeExplanation(
        hypothesis="Maybe variable comes from trusted source, not user input",
        why_considered="Variables could come from database, config files, hardcoded constants",
        why_rejected=(
            "F-string pattern and usage context suggest dynamic user input. "
            "Static/trusted values typically don't need regex. "
            "\n⚠️ FALSE POSITIVE ALERT: Could be false positive if variable actually "
            "comes from:\n"
            "- Database lookup (already validated data)\n"
            "- Configuration file (admin-controlled)\n"
            "- Hardcoded constant\n"
            "- Admin-only parameter with strict access controls\n"
            "Human analyst should trace variable origin in full codebase."
        ),
        based_on=[2]
    ))

    # Set legacy fields for backward compatibility
    reasoning.patterns_checked = [
        "MongoDB $regex operator usage",
        "F-string interpolation in regex patterns",
        "re.escape() sanitization function",
        "Input validation functions (validate_, sanitize_, isinstance)",
        "Regex metacharacter protection"
    ]

    reasoning.criteria_for_vulnerability = [
        "MongoDB $regex operator used in query",
        "User input embedded in regex pattern via f-string",
        "No re.escape() sanitization before regex use",
        "Pattern: {\"$regex\": f\"...{user_input}...\"}",
        "Regex metacharacters (.*|[]^$) can manipulate query logic"
    ]

    # Add to vulnerabilities list
    self.vulnerabilities.append({
        "type": "NOSQL_REGEX_INJECTION",
        "severity": "CRITICAL",
        "description": (
            "MongoDB $regex operator with unescaped user input allows regex injection "
            "attacks - CRITICAL: Attacker can inject regex metacharacters (.*,|,[],^,$) "
            "to manipulate query logic..."
        ),
        "recommendation": reasoning.conclusion.recommendation,
        "example_attack": reasoning.conclusion.attack_scenario,
        "detection_reasoning": reasoning.to_dict()  # Includes both new AND legacy formats
    })
    self.score = 0
```

## Key Improvements

### 1. Explicit Assumption Documentation
**Before**: "User input embedded directly in regex pattern string" (stated as fact)
**After**:
```python
Assumption(
    description="Variable is user-controlled",
    could_be_wrong_if=(
        "1. Variable comes from trusted source..., "
        "2. Variable is validated elsewhere..."
    )
)
```

### 2. "FALSE POSITIVE ALERT" in Alternatives
Each alternative explanation now includes explicit guidance for human analysts:
```python
"⚠️ FALSE POSITIVE ALERT: If validation exists in separate module/file,
this could be FALSE POSITIVE. Human analyst should check for:
- Middleware that validates all inputs
- Decorator on this function
- Calling code that pre-validates"
```

### 3. Confidence Levels
Different confidence for different assumptions:
- "Variable is user-controlled" → `confidence="high"` (strong evidence from f-string pattern)
- "Security-critical context" → `confidence="medium"` (less certain without full context)

### 4. Backward Compatibility
The `reasoning.to_dict()` method automatically generates legacy fields, so:
- Existing reports still work
- Existing tooling doesn't break
- New structure is additive, not breaking

## Benefits for Analysts

### Human Analyst Investigating False Positive

**Old approach** (read entire reasoning, figure out what to check):
- "Why vulnerable: User input embedded directly..."
- Analyst thinks: "Is it really user input though?"
- Has to read code to figure out all assumptions

**New approach** (check explicit assumptions):
1. Read Assumption #1: "Variable is user-controlled"
2. Read "Could be wrong if: Variable comes from trusted source..."
3. Check code: "Oh, variable comes from config file! That's the problem."
4. **False positive identified in 30 seconds**

### LLM Analyzer

```python
# Automated false positive detection
def analyze_false_positive(code: str, reasoning: dict) -> dict:
    """Check if any assumptions in reasoning are violated by actual code."""

    for assumption in reasoning['assumptions']:
        # Check each "could be wrong if" scenario
        for scenario in assumption['could_be_wrong_if'].split(', '):
            if check_scenario_applies(code, scenario):
                return {
                    'false_positive': True,
                    'reason': f"Assumption '{assumption['description']}' is wrong",
                    'evidence': f"Code shows: {scenario}"
                }

    return {'false_positive': False}
```

## Migration Strategy

### Phase 1: High-Value Detectors First
Retrofit detectors that have the most false positives:
1. NoSQL injection detector ✓
2. Command injection detector
3. Path traversal detector
4. IDOR detector

### Phase 2: Document Patterns
As we retrofit, document common assumption patterns:
- "Variable is user-controlled"
- "No validation exists"
- "Security-critical context"
- "No sanitization elsewhere"

### Phase 3: Helper Functions
Create helpers for common reasoning patterns:
```python
def build_user_controlled_assumption(var_name: str, evidence: Observation) -> Assumption:
    """Standard assumption for user-controlled variables."""
    return Assumption(
        description=f"Variable '{var_name}' is user-controlled",
        based_on=[evidence.observation_id],
        why_we_assume_this="Appears to come from request parameters",
        could_be_wrong_if=(
            "1. Validated elsewhere in separate module, "
            "2. Comes from trusted source (database/config), "
            "3. Pre-sanitized before reaching this code"
        ),
        confidence="high"
    )
```

## Summary

The retrofit approach:
1. **Doesn't break existing code** - uses `to_dict()` for backward compatibility
2. **Makes assumptions explicit** - "could be wrong if" clauses
3. **Helps human analysts** - clear guidance on what to check
4. **Enables automated analysis** - LLMs can verify assumptions
5. **Incremental adoption** - retrofit high-value detectors first

The key insight: **Every assumption is a potential false positive source**. By documenting them explicitly, we enable efficient analysis and continuous improvement.
