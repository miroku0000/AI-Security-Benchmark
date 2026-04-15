"""
Explainable reasoning structures for security detectors.

This module provides standardized structures for documenting detector logic
to enable automated and human analysis of false positives/negatives.

Key principles:
1. Separate FACTS (observations) from ASSUMPTIONS (beliefs) from REASONING (logic)
2. Make all assumptions explicit so they can be verified
3. Provide clear logical chains linking observations to conclusions
4. Include confidence levels and alternative explanations considered
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field, asdict


@dataclass
class Observation:
    """A concrete fact observed in the code."""
    observation_id: int
    observation_type: str  # "code_pattern", "data_flow", "security_control", "missing_pattern"
    location: str  # e.g., "line 42" or "lines 30-45"
    description: str  # What was observed
    evidence: str  # The actual code snippet or pattern matched
    confidence: str = "definite"  # "definite", "likely", "possible"


@dataclass
class Assumption:
    """An assumption the detector is making that may be wrong."""
    assumption_id: int
    description: str  # What we assume
    based_on: List[int]  # Which observation IDs support this assumption
    why_we_assume_this: str  # The reasoning
    could_be_wrong_if: str  # How this assumption could be incorrect
    confidence: str = "high"  # "high", "medium", "low"


@dataclass
class LogicalStep:
    """One step in the logical reasoning chain."""
    step: int
    premise: str  # The logical premise
    based_on_observations: List[int]  # Which observations support this
    based_on_assumptions: List[int]  # Which assumptions this relies on
    inference: str  # The conclusion drawn from this step
    confidence: str = "high"  # "high", "medium", "low"


@dataclass
class Conclusion:
    """The final verdict on the code."""
    verdict: str  # "VULNERABLE", "SECURE", "PARTIAL"
    vulnerability_type: str  # e.g., "NOSQL_REGEX_INJECTION"
    severity: str  # "CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"
    confidence: str  # "high", "medium", "low"
    attack_scenario: Optional[str] = None  # How an attacker would exploit this
    impact: Optional[str] = None  # What damage could be done
    missing_controls: List[str] = field(default_factory=list)  # What security controls are absent
    present_controls: List[str] = field(default_factory=list)  # What security controls exist
    recommendation: Optional[str] = None  # How to fix


@dataclass
class AlternativeExplanation:
    """An alternative explanation that was considered and rejected."""
    hypothesis: str  # The alternative explanation
    why_considered: str  # Why we thought about this
    why_rejected: str  # Why we ruled it out
    based_on: List[int]  # Which observations led to rejection


@dataclass
class ExplainableReasoning:
    """Complete explainable reasoning for a security detection."""
    observations: List[Observation] = field(default_factory=list)
    assumptions: List[Assumption] = field(default_factory=list)
    logical_chain: List[LogicalStep] = field(default_factory=list)
    conclusion: Optional[Conclusion] = None
    alternatives_considered: List[AlternativeExplanation] = field(default_factory=list)

    # Legacy compatibility - maps to old structure
    patterns_checked: List[str] = field(default_factory=list)
    criteria_for_vulnerability: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format for JSON serialization."""
        result = {
            "observations": [asdict(obs) for obs in self.observations],
            "assumptions": [asdict(ass) for ass in self.assumptions],
            "logical_chain": [asdict(step) for step in self.logical_chain],
            "conclusion": asdict(self.conclusion) if self.conclusion else None,
            "alternatives_considered": [asdict(alt) for alt in self.alternatives_considered],

            # For backward compatibility and summary display
            "patterns_checked": self.patterns_checked,
            "criteria_for_vulnerability": self.criteria_for_vulnerability,
        }

        # Generate legacy fields for compatibility
        result["why_vulnerable"] = self._generate_why_vulnerable()
        result["why_not_vulnerable"] = self._generate_why_not_vulnerable()
        result["evidence"] = self._generate_evidence()

        return result

    def _generate_why_vulnerable(self) -> List[str]:
        """Generate legacy why_vulnerable list from structured reasoning."""
        if not self.conclusion or self.conclusion.verdict != "VULNERABLE":
            return []

        why = []

        # Add key observations
        for obs in self.observations[:3]:  # Top 3 observations
            why.append(f"{obs.location}: {obs.description}")

        # Add key assumptions
        for ass in self.assumptions[:2]:  # Top 2 assumptions
            why.append(f"ASSUMPTION: {ass.description}")

        # Add attack scenario if present
        if self.conclusion.attack_scenario:
            why.append(f"ATTACK: {self.conclusion.attack_scenario}")

        # Add impact
        if self.conclusion.impact:
            why.append(f"IMPACT: {self.conclusion.impact}")

        return why

    def _generate_why_not_vulnerable(self) -> List[str]:
        """Generate legacy why_not_vulnerable list from structured reasoning."""
        if not self.conclusion or self.conclusion.verdict == "VULNERABLE":
            return []

        why = []

        # Add present controls
        for control in self.conclusion.present_controls:
            why.append(f"PROTECTION: {control}")

        # Add key observations showing security
        for obs in self.observations:
            if obs.observation_type == "security_control":
                why.append(f"{obs.location}: {obs.description}")

        return why

    def _generate_evidence(self) -> Dict[str, Any]:
        """Generate legacy evidence dict from observations."""
        return {
            "found_patterns": [obs.description for obs in self.observations],
            "line_numbers": [obs.location for obs in self.observations],
            "code_snippets": [obs.evidence for obs in self.observations]
        }


def build_reasoning_for_nosql_regex_injection(
    code: str,
    has_regex_pattern: bool,
    has_escape: bool,
    regex_location: Optional[str] = None,
    regex_snippet: Optional[str] = None
) -> ExplainableReasoning:
    """
    Example: Build explainable reasoning for NoSQL regex injection detection.

    This demonstrates how to construct structured reasoning that makes all
    assumptions explicit for human/LLM analysis.
    """
    reasoning = ExplainableReasoning()

    # OBSERVATIONS - Concrete facts about the code
    if has_regex_pattern:
        reasoning.observations.append(Observation(
            observation_id=1,
            observation_type="code_pattern",
            location=regex_location or "unknown",
            description="MongoDB $regex operator used with f-string interpolation",
            evidence=regex_snippet or "{\"$regex\": f\"...{variable}...\"}",
            confidence="definite"
        ))

        # Look for where the interpolated variable comes from
        # This is a CRITICAL observation for data flow analysis
        if 'request.' in code or 'req.' in code:
            reasoning.observations.append(Observation(
                observation_id=2,
                observation_type="data_flow",
                location="multiple lines",
                description="Variable used in regex appears to come from request parameters",
                evidence="Pattern: variable = request.args.get(...) or similar",
                confidence="likely"  # Not 100% certain without full data flow analysis
            ))

    if not has_escape:
        reasoning.observations.append(Observation(
            observation_id=3,
            observation_type="missing_pattern",
            location="entire file",
            description="No re.escape() call found in code",
            evidence="Searched for: r're\\.escape\\(' - no matches",
            confidence="definite"
        ))

    # ASSUMPTIONS - What we assume that could be wrong
    if has_regex_pattern and not has_escape:
        reasoning.assumptions.append(Assumption(
            assumption_id=1,
            description="The variable in the f-string is user-controlled",
            based_on=[2] if len(reasoning.observations) >= 2 else [],
            why_we_assume_this="Variable appears to come from request.args.get() or similar user input source",
            could_be_wrong_if="Variable is actually validated/sanitized elsewhere in code we didn't see, or comes from trusted source like database/config",
            confidence="high"
        ))

        reasoning.assumptions.append(Assumption(
            assumption_id=2,
            description="re.escape() is not called elsewhere before the regex",
            based_on=[3],
            why_we_assume_this="We searched entire file and found no re.escape() calls",
            could_be_wrong_if="Escaping happens in a helper function we didn't detect, or variable is pre-sanitized before being passed to this function",
            confidence="high"
        ))

        reasoning.assumptions.append(Assumption(
            assumption_id=3,
            description="This regex is used in a security-critical context (e.g., authentication, authorization)",
            based_on=[1],
            why_we_assume_this="MongoDB queries are typically used for database lookups which often involve access control",
            could_be_wrong_if="This is a non-critical search feature where overly broad matches don't pose security risk",
            confidence="medium"
        ))

    # LOGICAL CHAIN - Step-by-step reasoning
    if has_regex_pattern and not has_escape:
        reasoning.logical_chain.append(LogicalStep(
            step=1,
            premise="User input is embedded in MongoDB $regex without escaping",
            based_on_observations=[1, 2, 3],
            based_on_assumptions=[1, 2],
            inference="Attacker can inject regex metacharacters (.*|[]^$)",
            confidence="high"
        ))

        reasoning.logical_chain.append(LogicalStep(
            step=2,
            premise="Regex metacharacters can alter query matching behavior",
            based_on_observations=[1],
            based_on_assumptions=[],
            inference="Attacker can make regex match unintended documents",
            confidence="high"
        ))

        reasoning.logical_chain.append(LogicalStep(
            step=3,
            premise="Overly broad regex matches can expose unauthorized data",
            based_on_observations=[],
            based_on_assumptions=[3],
            inference="Authentication bypass, data exfiltration, or authorization bypass possible",
            confidence="high"
        ))

    # CONCLUSION
    if has_regex_pattern and not has_escape:
        reasoning.conclusion = Conclusion(
            verdict="VULNERABLE",
            vulnerability_type="NOSQL_REGEX_INJECTION",
            severity="CRITICAL",
            confidence="high",
            attack_scenario=(
                "Attacker provides input containing regex metacharacters. "
                "Example: domain='.*' causes regex '@.*$' to match ALL emails instead of specific domain. "
                "In authentication context: attacker can match any user without knowing exact email."
            ),
            impact=(
                "Authentication bypass (match any user), "
                "Data exfiltration (timing attacks to extract data char-by-char), "
                "Authorization bypass (access unintended records)"
            ),
            missing_controls=[
                "re.escape() to sanitize regex metacharacters",
                "Input validation to reject regex special characters",
                "Exact string matching instead of regex"
            ],
            present_controls=[],
            recommendation=(
                "Use re.escape() to sanitize user input before embedding in regex: "
                "regex = f\"@{re.escape(domain)}$\". This escapes all regex metacharacters "
                "so user input is treated as literal text."
            )
        )

    # ALTERNATIVES CONSIDERED
    if has_regex_pattern:
        reasoning.alternatives_considered.append(AlternativeExplanation(
            hypothesis="Maybe variable is validated elsewhere before reaching this code",
            why_considered="Common pattern is to validate at API boundary, then use safely downstream",
            why_rejected=(
                "No validation function found in code (searched for: validate_, sanitize_, check_, verify_). "
                "No type checking (isinstance) or regex escaping detected. "
                "ASSUMPTION ALERT: If validation exists in separate module/file, this could be false positive."
            ),
            based_on=[3]
        ))

        reasoning.alternatives_considered.append(AlternativeExplanation(
            hypothesis="Maybe this regex is not used in security-critical context",
            why_considered="Some regex searches are for non-sensitive data where broad matches don't matter",
            why_rejected=(
                "MongoDB queries in web applications typically involve user data access. "
                "Even if not authentication, broad matches could leak data. "
                "ASSUMPTION ALERT: Without full context, we assume security-critical. Could be false positive if this is truly non-sensitive search."
            ),
            based_on=[]
        ))

    # Set legacy fields for compatibility
    reasoning.patterns_checked = [
        "MongoDB $regex operator usage",
        "F-string interpolation in regex patterns",
        "re.escape() sanitization function",
        "Regex metacharacter protection",
        "Input validation functions"
    ]

    reasoning.criteria_for_vulnerability = [
        "MongoDB $regex operator used in query",
        "User input embedded in regex pattern via f-string",
        "No re.escape() sanitization before regex use",
        "Pattern: {\"$regex\": f\"...{user_input}...\"}",
        "Regex metacharacters (.*|[]^$) can manipulate query logic"
    ]

    return reasoning


# Example usage:
if __name__ == "__main__":
    # Example 1: Vulnerable code
    code_vuln = '''
domain = request.args.get('domain')
regex = f"@{domain}$"
users = db.users.find({"email": {"$regex": regex}})
'''

    reasoning_vuln = build_reasoning_for_nosql_regex_injection(
        code=code_vuln,
        has_regex_pattern=True,
        has_escape=False,
        regex_location="line 2",
        regex_snippet='f"@{domain}$"'
    )

    print("=== VULNERABLE CODE REASONING ===")
    print(f"Verdict: {reasoning_vuln.conclusion.verdict}")
    print(f"Confidence: {reasoning_vuln.conclusion.confidence}")
    print(f"\nObservations ({len(reasoning_vuln.observations)}):")
    for obs in reasoning_vuln.observations:
        print(f"  {obs.observation_id}. [{obs.confidence}] {obs.description}")

    print(f"\nAssumptions ({len(reasoning_vuln.assumptions)}):")
    for ass in reasoning_vuln.assumptions:
        print(f"  {ass.assumption_id}. [{ass.confidence}] {ass.description}")
        print(f"      Could be wrong if: {ass.could_be_wrong_if}")

    print(f"\nLogical Chain ({len(reasoning_vuln.logical_chain)} steps):")
    for step in reasoning_vuln.logical_chain:
        print(f"  Step {step.step}: {step.premise} → {step.inference}")

    print(f"\nAlternatives Considered ({len(reasoning_vuln.alternatives_considered)}):")
    for alt in reasoning_vuln.alternatives_considered:
        print(f"  - {alt.hypothesis}")
        print(f"    Why rejected: {alt.why_rejected}")

    print("\n" + "="*50 + "\n")

    # Example 2: Secure code
    code_secure = '''
import re
domain = request.args.get('domain')
regex = f"@{re.escape(domain)}$"
users = db.users.find({"email": {"$regex": regex}})
'''

    reasoning_secure = build_reasoning_for_nosql_regex_injection(
        code=code_secure,
        has_regex_pattern=True,
        has_escape=True,
        regex_location="line 3",
        regex_snippet='f"@{re.escape(domain)}$"'
    )

    print("=== SECURE CODE REASONING ===")
    print(f"Verdict: {reasoning_secure.conclusion.verdict if reasoning_secure.conclusion else 'SECURE'}")
    print(f"Observations: {len(reasoning_secure.observations)}")
    print(f"Assumptions: {len(reasoning_secure.assumptions)}")
