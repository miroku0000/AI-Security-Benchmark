# Detector Design Review & Recommendations

**Date**: 2026-04-01
**Status**: Architectural review based on Iteration 9 findings
**Purpose**: Propose fundamental redesign to address detector accuracy issues

---

## Executive Summary

Iteration 9 revealed that surface-level fixes (comment filtering, syntax validation) **failed to improve detector consistency** and in fact **made the problem worse** (347→355 inconsistencies).

This suggests the problem is **architectural**, not tactical. Regex-based pattern matching is fundamentally unsuitable for semantic security analysis.

**Recommendation**: Redesign detectors using **AST-based semantic analysis** with explicit security models.

---

## Current Architecture Problems

### Problem 1: Regex Pattern Matching is Brittle

**Current Approach**:
```python
# Example from test_access_control.py
idor_patterns = [
    (r'\.query\.filter_by\([^)]*id\s*=\s*[^)]+\)\.first\(\)',
     'Database query by ID without ownership check'),
    (r'\.query\.get\([^)]+\)',
     'Database query with get() without ownership check'),
]
```

**Problems**:
1. **Style dependent**: Whitespace, formatting, variable naming affect matching
2. **Incomplete**: Can't capture all syntactic variations
3. **False positives**: Matches patterns that aren't actually vulnerable
4. **False negatives**: Misses vulnerabilities expressed differently

**Example False Positive**:
```python
# SECURE code flagged as vulnerable
result = db.query.filter_by(id=safe_id).first()  # ID already validated
if result.user_id == current_user.id:  # Ownership check AFTER query
    return result
```

Detector sees `.filter_by(...id=...)` pattern and flags it, even though ownership check exists.

---

### Problem 2: Comment Filtering is Insufficient

**Hypothesis**: Comments cause style sensitivity
**Fix Attempted**: Filter out prompt metadata comments
**Result**: No improvement (access_001 still 3 SECURE / 3 VULNERABLE)

**Why It Didn't Work**:
1. Comments aren't the real issue - **code structure differences** are
2. Detector relies on specific patterns that vary between models
3. Filtering removes metadata but not structural variation

**Example**:
```python
# Both are secure, but detector sees them differently

# Version A (Claude Opus): VULNERABLE (2/4)
cursor = conn.cursor()
cursor.execute("SELECT * FROM orders WHERE user_id = ? AND order_id = ?",
               (user_id, order_id))

# Version B (Cursor): SECURE (4/4)
cur = conn.cursor()  # Different variable name
cur.execute("SELECT * FROM orders WHERE user_id = ? AND order_id = ?",
            (user_id, order_id),)  # Trailing comma
```

Variable naming (`cursor` vs `cur`) and trailing commas shouldn't affect security, but they might affect pattern matching.

---

### Problem 3: Syntax Validation Creates New Inconsistencies

**Fix Attempted**: Add syntax validation to catch broken code
**Result**: 8 new inconsistencies (tests moved from "always secure" to "inconsistent")

**Why It Backfired**:
- Syntax validation is **binary** (valid/invalid)
- Other detectors may give **partial credit** for broken code
- This creates inconsistency where none existed

**Example**:
```
BEFORE (all detectors say): Code is broken but has some security patterns → SECURE (partial credit)
AFTER (universal_fallback says): Code has syntax errors → VULNERABLE (0 points)
        (other detector says): Code has security patterns → SECURE (partial credit)
RESULT: INCONSISTENT verdicts
```

---

### Problem 4: No Semantic Understanding

**Current**: Detectors match text patterns
**Needed**: Detectors understand code semantics

**Example: IDOR Detection**

**Current Regex Approach**:
```python
# Matches: .filter_by(...id=...)
# Checks: Does "current_user" appear in same file?
# Problem: Can't determine WHEN or HOW it's checked
```

**Semantic Approach**:
```python
# Parse code into AST
# Find database query nodes
# Trace data flow to see if:
#   1. Query includes user-controlled ID parameter
#   2. Result is filtered by current_user BEFORE use
#   3. Authorization check is present
# If ID used without authorization → VULNERABLE
```

---

## Proposed Architecture: AST-Based Semantic Analysis

### Overview

**Current**: `code (string)` → `regex patterns` → `vulnerabilities`
**Proposed**: `code (string)` → `AST (tree)` → `semantic analysis` → `security model` → `vulnerabilities`

---

### Phase 1: Language-Specific AST Parsing

**Python**: Use `ast` module (already imported in universal_fallback)

```python
import ast

def parse_python(code: str) -> ast.Module:
    """Parse Python code into AST."""
    try:
        return ast.parse(code)
    except SyntaxError:
        return None  # Broken code
```

**JavaScript**: Use `esprima` or `acorn` (external libraries)

```python
import esprima

def parse_javascript(code: str) -> dict:
    """Parse JavaScript code into AST."""
    try:
        return esprima.parseScript(code)
    except:
        return None  # Broken code
```

**Other Languages**: Use language-specific parsers
- **Go**: `tree-sitter-go`
- **Rust**: `syn` (via Python bindings)
- **Java**: `javalang`
- **C#**: `tree-sitter-c-sharp`

---

### Phase 2: Security-Specific AST Visitors

**Example: IDOR Detector**

```python
class IDORVisitor(ast.NodeVisitor):
    """
    Detect IDOR vulnerabilities in Python code using AST.

    Checks:
    1. Find database query calls
    2. Check if they use ID parameters
    3. Verify ownership check exists BEFORE result use
    """

    def __init__(self):
        self.vulnerabilities = []
        self.has_ownership_check = False

    def visit_Call(self, node: ast.Call):
        """Visit function calls to find database queries."""
        # Check if this is a database query
        if self._is_db_query(node):
            # Check if it uses an ID parameter
            if self._uses_id_parameter(node):
                # Check if ownership verification exists
                if not self._has_ownership_check_before(node):
                    self.vulnerabilities.append({
                        'type': 'IDOR',
                        'line': node.lineno,
                        'description': 'Query by ID without ownership check'
                    })

        self.generic_visit(node)

    def _is_db_query(self, node: ast.Call) -> bool:
        """Check if call is a database query."""
        # Example: obj.query.filter_by(...)
        if isinstance(node.func, ast.Attribute):
            if node.func.attr in ['filter_by', 'get', 'find_one']:
                return True
        return False

    def _uses_id_parameter(self, node: ast.Call) -> bool:
        """Check if query uses 'id' parameter."""
        for keyword in node.keywords:
            if keyword.arg in ['id', 'order_id', 'user_id']:
                return True
        return False

    def _has_ownership_check_before(self, node: ast.Call) -> bool:
        """
        Check if ownership verification exists before result use.
        This requires control flow analysis.
        """
        # TODO: Implement data flow analysis
        # For now, check if "current_user" comparison exists in function
        return False  # Conservative: assume vulnerable unless proven safe
```

**Benefits**:
1. **Style agnostic**: Variable names, whitespace don't matter
2. **Semantic**: Understands code structure, not just text
3. **Precise**: Line numbers, exact nodes
4. **Extensible**: Easy to add new checks

---

### Phase 3: Control Flow & Data Flow Analysis

**Problem**: Simple AST visiting isn't enough - need to trace data through code.

**Example**:
```python
def get_order(user_id, order_id):
    result = db.query.filter_by(id=order_id).first()  # Looks vulnerable
    if result.user_id == user_id:  # But ownership checked HERE
        return result
    return None  # Unauthorized access prevented
```

**Solution**: Build control flow graph (CFG) and trace data.

```python
class CFGBuilder:
    """Build control flow graph from AST."""

    def build(self, tree: ast.Module) -> ControlFlowGraph:
        """Convert AST to CFG."""
        cfg = ControlFlowGraph()

        # Walk AST and build nodes/edges
        for stmt in ast.walk(tree):
            if isinstance(stmt, ast.If):
                # Create branch nodes
                cfg.add_branch(stmt.test, stmt.body, stmt.orelse)
            elif isinstance(stmt, ast.Return):
                # Create return node
                cfg.add_return(stmt.value)
            # ... handle other statement types

        return cfg

class DataFlowAnalyzer:
    """Trace data through control flow graph."""

    def trace_variable(self, cfg: ControlFlowGraph, var_name: str) -> List[Node]:
        """Find all uses of a variable."""
        uses = []
        for node in cfg.nodes:
            if var_name in node.reads:
                uses.append(node)
        return uses

    def is_checked_before_use(self, db_query_node: Node, use_node: Node) -> bool:
        """Check if authorization happens between query and use."""
        path = cfg.path_between(db_query_node, use_node)
        for node in path:
            if self._is_authorization_check(node):
                return True
        return False
```

**This enables**:
- Detecting IDOR even when ownership check is after query
- Distinguishing validated vs unvalidated input
- Understanding authentication flow

---

### Phase 4: Security Model Definition

**Instead of**: Hard-coded regex patterns
**Use**: Explicit security models

```python
class SecurityModel:
    """
    Define security requirements for a vulnerability class.
    """

    def __init__(self, name: str):
        self.name = name
        self.sources = []  # Where untrusted data comes from
        self.sinks = []    # Where untrusted data causes harm
        self.sanitizers = []  # What makes data safe

# Example: SQL Injection Model
sql_injection_model = SecurityModel("SQL Injection")
sql_injection_model.sources = [
    "request.args.get",
    "request.form.get",
    "input()",
]
sql_injection_model.sinks = [
    "cursor.execute",
    "db.session.execute",
]
sql_injection_model.sanitizers = [
    "parameterized_query",  # Using ? placeholders
    "escape_sql_string",
]

# Detector uses model to find violations
def detect(cfg: ControlFlowGraph, model: SecurityModel) -> List[Vulnerability]:
    """Find data flows from sources to sinks without sanitization."""
    vulns = []

    # Find all source nodes (untrusted input)
    sources = [node for node in cfg.nodes if node.calls in model.sources]

    # Find all sink nodes (dangerous operations)
    sinks = [node for node in cfg.nodes if node.calls in model.sinks]

    # Check if tainted data reaches sink
    for source in sources:
        for sink in sinks:
            if cfg.has_path(source, sink):
                # Check if sanitizer is on path
                path = cfg.path_between(source, sink)
                if not any(node.calls in model.sanitizers for node in path):
                    vulns.append(Vulnerability(
                        type=model.name,
                        source=source,
                        sink=sink,
                        path=path
                    ))

    return vulns
```

**Benefits**:
1. **Declarative**: Security requirements are explicit
2. **Maintainable**: Easy to add sources/sinks/sanitizers
3. **Consistent**: Same logic applies across all languages
4. **Explainable**: Can show exact data flow path

---

## Implementation Roadmap

### Phase 1: Proof of Concept (2-3 weeks)

**Goal**: Demonstrate AST-based detection for ONE category (SQL Injection)

**Tasks**:
1. Implement AST parser for Python and JavaScript
2. Build simple AST visitor for SQL injection patterns
3. Create test suite with known vulnerable/secure code
4. Compare results to current regex-based detector
5. Measure false positive/negative rates

**Success Criteria**:
- AST detector has <5% false positive rate (vs current >10%)
- AST detector catches all vulnerable code in test suite
- AST detector is style-agnostic (same code different formatting = same result)

---

### Phase 2: Extended Detection (1-2 months)

**Goal**: Implement AST detection for core categories

**Categories**:
1. SQL Injection
2. Command Injection
3. Path Traversal
4. XSS
5. Broken Access Control (IDOR)

**Tasks**:
1. Build control flow graph builder
2. Implement data flow analyzer
3. Define security models for each category
4. Create detector classes using models
5. Extensive testing against benchmark

**Success Criteria**:
- All 5 categories have AST-based detectors
- False positive rate <5% across all categories
- False negative rate <1% (critical)
- Cross-model consistency >95%

---

### Phase 3: Full Migration (2-3 months)

**Goal**: Replace all regex-based detectors with AST-based

**Tasks**:
1. Extend to all languages (Go, Rust, Java, C#, PHP)
2. Implement remaining categories (~30 more)
3. Add language-specific security models
4. Create detector regression test suite
5. Performance optimization

**Success Criteria**:
- All detectors are AST-based
- Benchmark can be run with 100% AST detectors
- Performance acceptable (<2x slower than regex)
- Documentation complete

---

### Phase 4: Advanced Features (3-4 months)

**Goal**: Add sophisticated security analysis

**Features**:
1. **Inter-procedural analysis**: Track data across function calls
2. **Symbolic execution**: Understand complex conditionals
3. **Type inference**: Use type information for better accuracy
4. **Machine learning**: Learn patterns from labeled data

**Example: Inter-procedural**:
```python
def validate_user(user_id):
    user = db.query.get(user_id)  # Looks vulnerable
    if user.id != current_user.id:
        raise Unauthorized()
    return user

def get_order(order_id):
    user = validate_user(request.args.get('user_id'))  # But validated here!
    return user.orders.filter_by(id=order_id).first()  # Safe
```

Current detector would flag `db.query.get(user_id)` as vulnerable.
Inter-procedural analysis would see validation in calling context.

---

## Comparison: Regex vs AST

| Aspect | Regex-Based (Current) | AST-Based (Proposed) |
|--------|----------------------|---------------------|
| **Accuracy** | ~70-80% | >95% expected |
| **False Positives** | High (~15-20%) | Low (<5%) |
| **False Negatives** | Medium (~5-10%) | Very Low (<1%) |
| **Style Sensitivity** | Very High | None (style agnostic) |
| **Consistency** | Poor (45.7% inconsistent) | Excellent (>95% consistent) |
| **Maintainability** | Low (regex is opaque) | High (models are explicit) |
| **Extensibility** | Hard (add more patterns) | Easy (add to models) |
| **Performance** | Fast (string matching) | Slower (parsing overhead) |
| **Language Support** | Medium (regex per language) | Good (parsers available) |
| **Explainability** | Poor (regex match) | Excellent (show data flow) |

**Verdict**: AST-based approach is superior in every dimension except performance, which is acceptable trade-off for a benchmark tool.

---

## Alternative: Hybrid Approach

**Concern**: Full AST migration is expensive (6-12 months of work)

**Alternative**: Hybrid approach with staged migration

### Stage 1: Quick Wins (1 month)
1. Keep regex detectors for simple cases
2. Add AST validation layer on top
3. Use AST to filter out false positives

```python
class HybridDetector:
    """Use regex for initial scan, AST for validation."""

    def analyze(self, code: str) -> List[Vulnerability]:
        # Step 1: Regex scan (fast, finds candidates)
        candidates = self.regex_scan(code)

        # Step 2: AST validation (slower, filters false positives)
        tree = ast.parse(code)
        validated = []
        for vuln in candidates:
            if self.ast_validate(tree, vuln):
                validated.append(vuln)

        return validated
```

**Benefits**:
- Immediate improvement (filter false positives)
- Leverages existing regex patterns
- Incremental migration path

**Drawbacks**:
- Still has regex limitations
- Won't catch AST-only detectable issues
- Maintenance burden of two systems

---

## Recommended Next Steps

### Immediate (Week 1)
1. **Proof of concept**: Build AST-based SQL injection detector for Python
2. **Baseline**: Run on benchmark, measure false positive/negative rates
3. **Document**: Create technical specification for AST detector framework

### Short-term (Month 1)
4. **Extend**: Add JavaScript support to SQL injection detector
5. **Compare**: Run side-by-side with regex detector, analyze differences
6. **Decision**: Go/no-go on full AST migration based on results

### Medium-term (Months 2-3)
7. **Framework**: Build reusable AST analysis framework
8. **Core categories**: Migrate 5 most important categories to AST
9. **Testing**: Extensive validation against benchmark

### Long-term (Months 4-12)
10. **Full migration**: Move all categories to AST
11. **Advanced features**: Add control flow, data flow analysis
12. **Optimization**: Performance tuning, caching

---

## Conclusion

Iteration 9 proved that **surface-level fixes don't work**. The detector architecture is fundamentally limited by regex-based pattern matching.

**The path forward requires architectural change**:
- Move from **text patterns** to **semantic analysis**
- Use **AST parsing** instead of regex
- Define explicit **security models**
- Implement **data flow tracking**

This is a **significant investment** (6-12 months), but the alternative is continuing with detectors that:
- Have 45%+ inconsistency rates
- Generate false positives/negatives
- Can't be reliably improved

**Recommendation**: Begin with proof of concept (1 month) to validate approach, then commit to full migration if results are positive.

**Expected Outcome**: >95% consistency, <5% false positive rate, <1% false negative rate.
