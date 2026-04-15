"""
Helper functions for common explainable reasoning patterns.

These helpers make it faster to add explainable reasoning to detectors
by providing pre-built patterns for common assumptions and observations.
"""

from typing import List, Optional
from utils.explainable_reasoning import (
    Observation,
    Assumption,
    LogicalStep,
    Conclusion,
    AlternativeExplanation
)


def user_controlled_variable_assumption(
    assumption_id: int,
    var_name: str,
    based_on_observation: int,
    evidence: str = "request.get(), request.args, req.params, etc.",
    confidence: str = "high"
) -> Assumption:
    """
    Standard assumption: Variable is user-controlled.

    This is one of the most common assumptions that causes false positives.
    """
    return Assumption(
        assumption_id=assumption_id,
        description=f"Variable '{var_name}' is user-controlled (comes from untrusted input)",
        based_on=[based_on_observation],
        why_we_assume_this=(
            f"Variable appears to come from user input: {evidence}. "
            "Web applications typically receive user input via request parameters, "
            "form data, URL paths, or request bodies."
        ),
        could_be_wrong_if=(
            "1. Variable comes from trusted source: database query result, "
            "configuration file, hardcoded constant, environment variable, "
            "2. Variable is validated/sanitized in middleware, decorator, or calling function "
            "that we didn't analyze (separate module/file), "
            "3. Variable is pre-sanitized before being passed to this function, "
            "4. This is test/example code not used in production, "
            "5. Variable is admin-only parameter with strict access controls, "
            "6. Framework provides automatic input sanitization we're unaware of"
        ),
        confidence=confidence
    )


def no_sanitization_assumption(
    assumption_id: int,
    sanitization_type: str,
    based_on_observation: int,
    searched_patterns: List[str],
    confidence: str = "high"
) -> Assumption:
    """
    Standard assumption: No sanitization/escaping exists.

    Common false positive source: sanitization exists in separate module.
    """
    patterns_str = ", ".join(searched_patterns)

    return Assumption(
        assumption_id=assumption_id,
        description=f"No {sanitization_type} found in code",
        based_on=[based_on_observation],
        why_we_assume_this=(
            f"Searched entire file for {sanitization_type} patterns: {patterns_str}. "
            "No matches found. Sanitization typically happens near usage."
        ),
        could_be_wrong_if=(
            f"1. {sanitization_type} happens in helper function with different name "
            "(sanitize_input, clean_data, validate_param, etc.), "
            "2. Variable is pre-sanitized in calling code before being passed to this function, "
            "3. Framework/library provides automatic sanitization/escaping, "
            "4. Sanitization exists in separate module/file not analyzed, "
            "5. Custom sanitization with non-standard function name, "
            "6. Middleware handles sanitization before request reaches this code"
        ),
        confidence=confidence
    )


def security_critical_context_assumption(
    assumption_id: int,
    operation_type: str,
    based_on_observations: List[int],
    confidence: str = "medium"
) -> Assumption:
    """
    Standard assumption: Operation is security-critical.

    Often has medium confidence since we lack full application context.
    """
    return Assumption(
        assumption_id=assumption_id,
        description=f"This {operation_type} is used in security-critical context",
        based_on=based_on_observations,
        why_we_assume_this=(
            f"{operation_type} operations in web applications are typically used for "
            "authentication, authorization, data access control, or sensitive operations. "
            "Vulnerabilities in such contexts enable unauthorized access."
        ),
        could_be_wrong_if=(
            "1. This is a non-critical feature where vulnerability doesn't matter "
            "(public data search, demo/example endpoint, internal testing tool), "
            "2. Results are filtered by permissions layer after operation, "
            "3. This is admin-only tool where risk is acceptable, "
            "4. Operation only accesses public/non-sensitive data, "
            "5. Additional security controls exist downstream that we didn't detect"
        ),
        confidence=confidence
    )


def code_pattern_observation(
    observation_id: int,
    location: str,
    pattern_name: str,
    evidence: str,
    confidence: str = "definite"
) -> Observation:
    """Standard observation: Code pattern detected."""
    return Observation(
        observation_id=observation_id,
        observation_type="code_pattern",
        location=location,
        description=f"{pattern_name} detected",
        evidence=evidence,
        confidence=confidence
    )


def missing_pattern_observation(
    observation_id: int,
    pattern_name: str,
    searched_pattern: str,
    confidence: str = "definite"
) -> Observation:
    """Standard observation: Security control pattern NOT found."""
    return Observation(
        observation_id=observation_id,
        observation_type="missing_pattern",
        location="entire file",
        description=f"No {pattern_name} found in code",
        evidence=f"Searched for: {searched_pattern} - no matches",
        confidence=confidence
    )


def data_flow_observation(
    observation_id: int,
    var_name: str,
    source: str,
    location: str,
    evidence: str,
    confidence: str = "likely"
) -> Observation:
    """Standard observation: Data flow from source to usage."""
    return Observation(
        observation_id=observation_id,
        observation_type="data_flow",
        location=location,
        description=f"Variable '{var_name}' flows from {source}",
        evidence=evidence,
        confidence=confidence
    )


def validation_elsewhere_alternative(
    hypothesis_id: int,
    validation_type: str,
    based_on_observation: int
) -> AlternativeExplanation:
    """
    Standard alternative: Maybe validation exists elsewhere.

    This is THE most common false positive scenario.
    """
    return AlternativeExplanation(
        hypothesis=f"Maybe {validation_type} exists elsewhere before reaching this code",
        why_considered=(
            "Common architectural pattern: validate at API boundary (middleware, "
            "decorator, framework level), then use safely downstream in business logic."
        ),
        why_rejected=(
            f"No {validation_type} function found in this file (searched for: "
            "validate_, sanitize_, check_, verify_, isinstance, type checking). "
            "\n\n⚠️ FALSE POSITIVE ALERT: This is the #1 cause of false positives. "
            "If validation exists in separate module/file, middleware, decorator, "
            "or calling function that we didn't analyze, this IS a FALSE POSITIVE.\n\n"
            "Human analyst should check for:\n"
            "- Middleware that validates/sanitizes all inputs before routing\n"
            "- Decorator on this function that validates parameters (@validate, @sanitize)\n"
            "- Calling code that pre-validates before calling this function\n"
            "- Framework-level validation (Django forms, Pydantic models, Joi schemas)\n"
            "- Input validation in API gateway or reverse proxy\n"
            "- Validation in parent class methods (if this is OOP)\n\n"
            "To verify: Trace the full request flow from entry point to this code."
        ),
        based_on=[based_on_observation]
    )


def trusted_source_alternative(
    hypothesis_id: int,
    var_name: str,
    based_on_observation: int
) -> AlternativeExplanation:
    """Standard alternative: Maybe variable comes from trusted source."""
    return AlternativeExplanation(
        hypothesis=f"Maybe variable '{var_name}' comes from trusted source, not user input",
        why_considered=(
            "Variables can come from multiple sources: database queries, configuration "
            "files, environment variables, hardcoded constants, admin-controlled data."
        ),
        why_rejected=(
            f"Variable name, usage context, and code pattern suggest dynamic user input. "
            "Trusted/static data typically doesn't require dynamic operations. "
            "\n\n⚠️ FALSE POSITIVE ALERT: Could be false positive if variable actually comes from:\n"
            "- Database lookup returning already-validated data\n"
            "- Configuration file (YAML, JSON, .env) that's admin-controlled\n"
            "- Environment variable set during deployment\n"
            "- Hardcoded constant or enum value\n"
            "- Admin-only API parameter with strict authentication/authorization\n"
            "- Internal service-to-service call (not exposed to end users)\n\n"
            "Human analyst should: Trace variable origin in full codebase, check if "
            "this endpoint is public or internal-only, verify authentication requirements."
        ),
        based_on=[based_on_observation]
    )


def non_critical_context_alternative(
    hypothesis_id: int,
    operation_type: str,
    based_on_observations: List[int]
) -> AlternativeExplanation:
    """Standard alternative: Maybe operation is not security-critical."""
    return AlternativeExplanation(
        hypothesis=f"Maybe this {operation_type} is not in security-critical context",
        why_considered=(
            f"Not all {operation_type} operations involve sensitive data or access control. "
            "Some are for public features, demos, or non-critical functionality."
        ),
        why_rejected=(
            f"{operation_type} operations in web applications typically involve data access, "
            "which often includes user authentication, authorization, or sensitive information. "
            "Even if not authentication, vulnerabilities can leak data. "
            "\n\n⚠️ FALSE POSITIVE ALERT: Without full application context, we assume "
            "security-critical by default. This could be FALSE POSITIVE if:\n"
            "- Operation only accesses public/non-sensitive data (blog posts, public profiles)\n"
            "- Results are filtered by permissions layer after operation executes\n"
            "- This is internal admin tool where users are already highly trusted\n"
            "- Endpoint requires strict authentication and users can only affect their own data\n"
            "- This is demo/test endpoint not exposed in production\n\n"
            "Human analyst should check: (1) What data does this operation access? "
            "(2) Who can access this endpoint? (3) Are there downstream security controls?"
        ),
        based_on=based_on_observations
    )


def build_injection_reasoning_pattern(
    vulnerability_type: str,
    injection_vector: str,
    user_controlled_var: str,
    sanitization_missing: str,
    attack_example: str,
    impact: str,
    fix_recommendation: str
) -> dict:
    """
    Helper to build complete reasoning for injection vulnerabilities.

    Covers: SQL injection, NoSQL injection, command injection, LDAP injection, etc.

    Returns dict with common patterns pre-filled.
    """
    return {
        "patterns": {
            "user_controlled_variable": user_controlled_var,
            "missing_sanitization": sanitization_missing,
            "injection_vector": injection_vector
        },
        "attack_scenario": attack_example,
        "impact": impact,
        "recommendation": fix_recommendation,
        "common_assumptions": [
            "Variable is user-controlled (could be from database/config)",
            f"No {sanitization_missing} exists (could be in separate module)",
            "Operation is security-critical (could be non-sensitive feature)"
        ],
        "common_alternatives": [
            "validation_elsewhere",
            "trusted_source",
            "non_critical_context"
        ]
    }


# Example: Pre-configured patterns for common vulnerability types

COMMAND_INJECTION_PATTERN = build_injection_reasoning_pattern(
    vulnerability_type="COMMAND_INJECTION",
    injection_vector="os.system(), subprocess.call(), shell=True",
    user_controlled_var="Variable from request.get(), request.args, req.params",
    sanitization_missing="shlex.quote(), pipes.quote(), input validation",
    attack_example=(
        "Input: 'file.txt; rm -rf /' → Command becomes: 'cat file.txt; rm -rf /' → "
        "Executes arbitrary commands, deletes files, installs backdoor"
    ),
    impact="Complete system compromise, data destruction, backdoor installation, privilege escalation",
    fix_recommendation="Use shlex.quote() to escape shell metacharacters, or avoid shell=True entirely"
)

SQL_INJECTION_PATTERN = build_injection_reasoning_pattern(
    vulnerability_type="SQL_INJECTION",
    injection_vector="String concatenation in SQL query, f-strings, .format()",
    user_controlled_var="Variable from request.form, request.args, req.body",
    sanitization_missing="Parameterized queries (?), SQLAlchemy ORM, prepared statements",
    attack_example=(
        "Input: \"admin' OR '1'='1\" → Query becomes: SELECT * FROM users WHERE username='admin' OR '1'='1' → "
        "Bypasses authentication, returns all users"
    ),
    impact="Authentication bypass, data exfiltration, data modification, complete database compromise",
    fix_recommendation="Use parameterized queries: cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))"
)

PATH_TRAVERSAL_PATTERN = build_injection_reasoning_pattern(
    vulnerability_type="PATH_TRAVERSAL",
    injection_vector="open(), send_file(), os.path.join() with user input",
    user_controlled_var="Filename/path from request.args, request.form, req.params",
    sanitization_missing="os.path.abspath(), path normalization, whitelist validation",
    attack_example=(
        "Input: '../../etc/passwd' → Path becomes: '/app/files/../../etc/passwd' → "
        "Reads /etc/passwd, leaks system credentials"
    ),
    impact="Arbitrary file read, source code disclosure, credential theft, configuration exposure",
    fix_recommendation="Validate filename is in whitelist, use os.path.abspath() and check if result is in allowed directory"
)

XSS_PATTERN = build_injection_reasoning_pattern(
    vulnerability_type="XSS",
    injection_vector="HTML rendering without escaping, innerHTML, document.write()",
    user_controlled_var="User input rendered in HTML response",
    sanitization_missing="HTML escaping, DOMPurify, template auto-escaping",
    attack_example=(
        "Input: '<script>fetch(\"/api/steal?cookie=\"+document.cookie)</script>' → "
        "Rendered in HTML → Executes JavaScript, steals session cookie"
    ),
    impact="Session hijacking, account takeover, phishing, malware distribution, defacement",
    fix_recommendation="Use template engine with auto-escaping (Jinja2 autoescape, React JSX), or manually escape with html.escape()"
)
