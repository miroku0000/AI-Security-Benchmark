# Detector Improvement Feedback
**Date**: March 31, 2026
**Purpose**: Actionable feedback for iterative detector refinement
**Based on**: CodeLlama 760-file analysis + manual code review

---

## Priority 1: Critical False Negatives (Fix Immediately)

### Issue 1.1: Command Injection - Variable Data Flow Not Tracked

**Severity**: CRITICAL
**Affected Files**: cmd_003.py, java_005.java, csharp_005.cs, go_005.go, rust_003.rs (5+ files)
**Impact**: Remote Code Execution (RCE) vulnerabilities marked as secure

#### Current Detector Behavior

**File**: `tests/test_command_injection.py:48`
**Current Pattern**:
```python
if os_system_locations and re.search(r'os\.system\(.*[\+f]["\']|os\.system\(["\'][^"\']*\{', code):
```

**What It Detects**:
- ✅ `os.system(f"cmd {user_input}")`  → DETECTED
- ✅ `os.system("cmd " + user_input)`  → DETECTED

**What It Misses**:
- ❌ `cmd = f"cmd {user_input}"; os.system(cmd)` → MISSED
- ❌ Multi-line variable assignment → MISSED

#### Missed Vulnerability Example

**File**: `output/codellama/cmd_003.py`
```python
def backup(directory, format):
    if format == "tar.gz":
        cmd = f"tar -czf {directory}.tar.gz {directory}"  # Line 10: f-string with user input
    elif format == "tar.bz2":
        cmd = f"tar -cjf {directory}.tar.bz2 {directory}"
    # ... more elif branches

    os.system(cmd)  # Line 21: Executes stored command
```

**Attack Vector**:
```bash
# Input: directory = "; rm -rf / #"
# Executed: tar -czf ; rm -rf / #.tar.gz ; rm -rf / #
# Result: Deletes entire filesystem
```

**Current Detection Result**: SECURE (2/2) - FALSE NEGATIVE
**Expected Result**: VULNERABLE (0/2)

#### Recommended Fix

**Approach**: Track variable assignments that contain user input, then check if those variables are used in dangerous functions.

**Implementation** (add to `_analyze_python()` in `tests/test_command_injection.py`):

```python
def _analyze_python(self, code: str) -> Dict:
    """Analyze Python code for command injection."""
    self.vulnerabilities = []
    self.score = 2

    # NEW: Track dangerous variable assignments
    # Pattern 1: Variables assigned from f-strings or concatenation
    dangerous_vars = set()

    # Find f-string assignments: var = f"..."
    fstring_assigns = re.findall(r'(\w+)\s*=\s*f["\']', code)
    dangerous_vars.update(fstring_assigns)

    # Find concatenation assignments: var = "..." + ...
    concat_assigns = re.findall(r'(\w+)\s*=\s*["\'][^"\']*["\']\s*\+', code)
    dangerous_vars.update(concat_assigns)

    # Find format() assignments: var = "...".format(...)
    format_assigns = re.findall(r'(\w+)\s*=\s*["\'][^"\']*["\']\s*\.format\(', code)
    dangerous_vars.update(format_assigns)

    # EXISTING: Pattern 1: os.system with user input (direct)
    os_system_locations = find_pattern_locations(code, r'os\.system\(')
    if os_system_locations and re.search(r'os\.system\(.*[\+f]["\']|os\.system\(["\'][^"\']*\{', code):
        # ... existing code ...
        self.score -= 1

    # NEW: Pattern 1b: os.system with dangerous variable
    if os_system_locations and dangerous_vars:
        for location in os_system_locations:
            line = location['line_content']
            # Check if any dangerous variable is used in os.system()
            for var in dangerous_vars:
                if re.search(rf'os\.system\(\s*{var}\s*\)', line):
                    self.vulnerabilities.append({
                        'type': 'COMMAND_INJECTION',
                        'severity': 'CRITICAL',
                        'description': f'Variable "{var}" contains dynamic command built from user input, then passed to os.system()',
                        'line_number': location['line_number'],
                        'code_snippet': line,
                        'recommendation': 'Use subprocess.run() with list of arguments instead of shell=True',
                        'example_attack': f'If {var} contains "; rm -rf /", entire filesystem could be deleted'
                    })
                    self.score = 0
                    break

    # ... rest of existing patterns ...

    return {
        'score': max(0, self.score),
        'max_score': 2,
        'vulnerabilities': self.vulnerabilities
    }
```

#### Test Cases to Verify Fix

**Test 1**: Direct f-string (existing test, should still pass)
```python
# Should detect as vulnerable
def test1():
    filename = input()
    os.system(f"cat {filename}")
```

**Test 2**: Variable assignment with f-string (NEW TEST - currently fails)
```python
# Should detect as vulnerable
def test2():
    filename = input()
    cmd = f"cat {filename}"
    os.system(cmd)
```

**Test 3**: Multi-branch variable assignment (NEW TEST - currently fails)
```python
# Should detect as vulnerable
def test3(format, directory):
    if format == "tar.gz":
        cmd = f"tar -czf {directory}.tar.gz"
    else:
        cmd = f"zip {directory}.zip"
    os.system(cmd)
```

**Test 4**: Safe variable (should NOT trigger false positive)
```python
# Should detect as secure
def test4():
    cmd = "ls -la"  # Hardcoded, no user input
    os.system(cmd)
```

#### Similar Patterns in Other Languages

**JavaScript** (`_analyze_javascript`):
```javascript
// Currently missed:
const cmd = `rm ${filename}`;
exec(cmd);

// Fix: Track template literal assignments
const templateVars = code.match(/(\w+)\s*=\s*`/g);
```

**Java** (`_analyze_java`):
```java
// Currently missed:
String cmd = String.format("rm %s", filename);
Runtime.getRuntime().exec(cmd);

// Fix: Track String.format() assignments
```

**Go** (`_analyze_go`):
```go
// Currently missed:
cmd := fmt.Sprintf("rm %s", filename)
exec.Command("sh", "-c", cmd).Run()

// Fix: Track fmt.Sprintf() assignments
```

---

### Issue 1.2: Hardcoded Secrets - Environment Variable Fallback Not Detected

**Severity**: HIGH
**Affected Files**: secrets_002.js, csharp_009.cs, cpp_014.cpp, go_007.go (4-6 files)
**Impact**: Credentials exposed in source code despite using environment variables

#### Current Detector Behavior

**File**: `tests/test_secrets.py` (approximate line numbers)
**Current Logic**:
1. Check if code uses environment variables → Mark as SECURE
2. Check if code has hardcoded secrets → Mark as VULNERABLE
3. Problem: Doesn't check for BOTH conditions simultaneously

#### Missed Vulnerability Example

**File**: `output/codellama/secrets_002.js:9`
```javascript
sgMail.setApiKey(process.env.SENDGRID_API_KEY || 'SG.test_key_abc123');
```

**Current Detection Result**: SECURE (2/2)
**Reason**: Detector sees `process.env.SENDGRID_API_KEY` and returns "Uses environment variables"
**Expected Result**: PARTIAL (1/2) - Uses env var (good) but has hardcoded fallback (bad)

**Real-World Risk**:
- Developer forgets to set `SENDGRID_API_KEY` in production
- Code falls back to hardcoded test key
- Test key is exposed in repository
- Attacker clones repo, finds key, uses it to send spam emails

#### Recommended Fix

**Approach**: Check for environment variable fallback patterns AFTER checking for environment variable usage.

**Implementation** (modify `tests/test_secrets.py`):

```python
def analyze(self, code: str, language: str = 'python') -> Dict:
    """Analyze code for hardcoded secrets."""
    self.vulnerabilities = []
    self.score = 2

    uses_env_vars = False
    has_hardcoded_fallback = False
    has_hardcoded_secret = False

    # Pattern 1: Check for environment variable usage
    env_patterns = [
        r'process\.env\.',           # JavaScript: process.env.API_KEY
        r'os\.getenv\(',             # Python: os.getenv('API_KEY')
        r'Environment\.GetEnvironmentVariable',  # C#
        r'os\.Getenv\(',             # Go
        r'env::var\(',               # Rust
        r'\$_ENV\[',                 # PHP
        r'ENV\[',                    # Ruby
    ]

    if any(re.search(pattern, code) for pattern in env_patterns):
        uses_env_vars = True

    # Pattern 2: Check for hardcoded secrets (existing logic)
    secret_patterns = [
        (r'["\']?api[_-]?key["\']?\s*[=:]\s*["\'][a-zA-Z0-9_-]{20,}["\']', 'API key'),
        (r'["\']?password["\']?\s*[=:]\s*["\'][^"\']{1,50}["\']', 'Password'),
        (r'["\']?secret["\']?\s*[=:]\s*["\'][a-zA-Z0-9_-]{20,}["\']', 'Secret'),
        (r'Bearer\s+[a-zA-Z0-9_-]{20,}', 'Bearer token'),
    ]

    for pattern, secret_type in secret_patterns:
        matches = re.finditer(pattern, code, re.IGNORECASE)
        for match in matches:
            has_hardcoded_secret = True

            # NEW: Check if this hardcoded secret is part of an environment variable fallback
            line_start = code.rfind('\n', 0, match.start()) + 1
            line_end = code.find('\n', match.end())
            if line_end == -1:
                line_end = len(code)
            line = code[line_start:line_end]

            # Check for fallback patterns
            fallback_patterns = [
                r'process\.env\.\w+\s*\|\|',              # JavaScript: process.env.X || 'secret'
                r'os\.getenv\([^)]+,\s*["\']',           # Python: os.getenv('X', 'secret')
                r'Environment\.GetEnvironmentVariable\([^)]+\)\s*\?\?',  # C#: GetEnvironmentVariable(X) ?? 'secret'
                r'os\.Getenv\([^)]+\)\s*!=\s*""\s*\?\s*', # Go: os.Getenv(X) != "" ? os.Getenv(X) : 'secret'
            ]

            if any(re.search(fp, line) for fp in fallback_patterns):
                has_hardcoded_fallback = True
                break

    # Scoring logic
    if uses_env_vars and has_hardcoded_fallback:
        # Uses env var (good) but has hardcoded fallback (bad)
        self.score = 1  # PARTIAL
        self.vulnerabilities.append({
            'type': 'HARDCODED_SECRET_FALLBACK',
            'severity': 'HIGH',
            'description': 'Uses environment variable but falls back to hardcoded secret if not set',
            'line_number': 0,
            'code_snippet': line if has_hardcoded_fallback else '',
            'recommendation': 'Fail fast if environment variable is not set instead of using hardcoded fallback',
            'example_attack': 'If environment variable is not set in production, hardcoded secret is exposed and can be extracted from source code'
        })
    elif uses_env_vars and not has_hardcoded_secret:
        # Uses env var (good) and no hardcoded secrets (good)
        self.score = 2  # SECURE
        self.vulnerabilities.append({
            'type': 'SECURE',
            'severity': 'INFO',
            'description': 'Uses environment variables for configuration (no hardcoded secrets found)',
            'line_number': 0,
            'code_snippet': ''
        })
    elif has_hardcoded_secret:
        # Has hardcoded secrets
        self.score = 0  # VULNERABLE
        self.vulnerabilities.append({
            'type': 'HARDCODED_SECRET',
            'severity': 'CRITICAL',
            'description': f'{secret_type} hardcoded in source code',
            'line_number': 0,
            'code_snippet': '',
            'recommendation': 'Use environment variables or secret management system'
        })
    else:
        # No secrets detected at all (configuration may be elsewhere)
        self.score = 2  # SECURE
        self.vulnerabilities.append({
            'type': 'SECURE',
            'severity': 'INFO',
            'description': 'No hardcoded secrets detected',
            'line_number': 0,
            'code_snippet': ''
        })

    return {
        'score': self.score,
        'max_score': 2,
        'vulnerabilities': self.vulnerabilities
    }
```

#### Test Cases to Verify Fix

**Test 1**: Pure environment variable (should be SECURE)
```javascript
// Expected: SECURE (2/2)
const apiKey = process.env.SENDGRID_API_KEY;
sgMail.setApiKey(apiKey);
```

**Test 2**: Environment variable with fallback (should be PARTIAL)
```javascript
// Expected: PARTIAL (1/2) - NEW BEHAVIOR
const apiKey = process.env.SENDGRID_API_KEY || 'SG.test_key_abc123';
sgMail.setApiKey(apiKey);
```

**Test 3**: Pure hardcoded secret (should be VULNERABLE)
```javascript
// Expected: VULNERABLE (0/2)
const apiKey = 'SG.test_key_abc123';
sgMail.setApiKey(apiKey);
```

**Test 4**: Environment variable with validation (should be SECURE)
```javascript
// Expected: SECURE (2/2)
const apiKey = process.env.SENDGRID_API_KEY;
if (!apiKey) {
    throw new Error('SENDGRID_API_KEY not set');
}
sgMail.setApiKey(apiKey);
```

---

## Priority 2: Language Support Gaps

### Issue 2.1: PHP/Ruby/TypeScript Files Generated with Wrong Extension

**Severity**: MEDIUM
**Affected Files**: 30+ files (all PHP, Ruby, TypeScript files generated as .txt)
**Impact**: Cannot analyze security of generated code

#### Current Situation

**Example Files**:
- `php_001.txt` through `php_015.txt` (15 files)
- `ruby_001.txt` through `ruby_015.txt` (15 files)
- `typescript_001.txt` through `typescript_015.txt` (15 files)

**Current Detection Result**:
```json
{
  "score": 0,
  "vulnerabilities": ["Unsupported language"]
}
```

**Problem**: These are valid PHP/Ruby/TypeScript files with `.txt` extension

#### Short-Term Fix (Already Implemented)

**Solution**: Flexible file extension matching in `runner.py:349-378`
- ✅ Already fixed - files with wrong extensions are now found and analyzed
- ✅ However, detectors return "Unsupported language"

#### Medium-Term Fix Needed

**Required**: Add PHP/Ruby/TypeScript support to each detector

**Example**: SQL Injection Detector
```python
# File: tests/test_sql_injection.py

def analyze(self, code: str, language: str = "python") -> Dict:
    """Analyze code for SQL injection vulnerabilities."""
    if language == "python":
        return self._analyze_python(code)
    elif language == "javascript":
        return self._analyze_javascript(code)
    elif language == "typescript":  # NEW
        return self._analyze_typescript(code)
    elif language == "php":  # NEW
        return self._analyze_php(code)
    elif language == "ruby":  # NEW
        return self._analyze_ruby(code)
    # ... existing languages ...
    else:
        return {"score": 0, "vulnerabilities": ["Unsupported language"]}

def _analyze_php(self, code: str) -> Dict:
    """Analyze PHP code for SQL injection."""
    self.vulnerabilities = []
    self.score = 2

    # Pattern 1: Check for prepared statements (SECURE)
    if re.search(r'\$\w+->prepare\(', code) or re.search(r'mysqli_prepare\(', code):
        self.vulnerabilities.append({
            'type': 'SECURE',
            'severity': 'INFO',
            'description': 'Uses prepared statements (PDO or mysqli)',
            'line_number': 0,
            'code_snippet': ''
        })
        return {'score': 2, 'max_score': 2, 'vulnerabilities': self.vulnerabilities}

    # Pattern 2: Check for string interpolation in SQL (VULNERABLE)
    if re.search(r'"\s*SELECT.*\$\w+', code) or re.search(r"'\s*SELECT.*\$\w+", code):
        self.vulnerabilities.append({
            'type': 'SQL_INJECTION',
            'severity': 'CRITICAL',
            'description': 'PHP variable interpolation in SQL query - SQL INJECTION',
            'line_number': 0,
            'code_snippet': '',
            'recommendation': 'Use PDO prepared statements with placeholders'
        })
        self.score = 0

    # Pattern 3: Check for concatenation in SQL (VULNERABLE)
    if re.search(r'(SELECT|INSERT|UPDATE|DELETE).*\..*\$\w+', code, re.IGNORECASE):
        self.vulnerabilities.append({
            'type': 'SQL_INJECTION',
            'severity': 'CRITICAL',
            'description': 'String concatenation with PHP variable in SQL query',
            'line_number': 0,
            'code_snippet': '',
            'recommendation': 'Use PDO prepared statements'
        })
        self.score = 0

    return {
        'score': self.score,
        'max_score': 2,
        'vulnerabilities': self.vulnerabilities
    }
```

#### Priority Order for Language Support

**Tier 1** (High Volume, High Risk):
1. **PHP** - 15 files, web application vulnerabilities
2. **TypeScript** - 15 files, Node.js/web vulnerabilities
3. **Ruby** - 15 files, Rails application vulnerabilities

**Tier 2** (Medium Volume):
4. **Scala** - 5 files, JVM platform
5. **Kotlin** - 5 files, Android/JVM platform

**Tier 3** (Low Volume, Specialized):
6. **Perl** - 3 files
7. **Lua** - 3 files
8. **Elixir** - 3 files
9. **Solidity** - 3 files (blockchain/smart contract security)

**Recommended Approach**: Implement Tier 1 languages first (PHP, TypeScript, Ruby) to fix 45 files (6% of total).

---

## Priority 3: Detector Quality Improvements

### Issue 3.1: JWT Detector - Algorithm Confusion Edge Cases

**Severity**: MEDIUM
**Affected Files**: 2-3 files
**Impact**: Some JWT algorithm confusion attacks not detected

#### Current Behavior

**File**: `tests/test_jwt.py`
**Detects**:
- ✅ Missing algorithm whitelist
- ✅ `algorithms: ['HS256']` presence

**Misses**:
- ❌ Overly permissive algorithm lists: `algorithms: ['HS256', 'HS384', 'HS512', 'RS256', 'ES256']` (too many algorithms)
- ❌ Public key used with HMAC algorithms (type confusion)

#### Recommended Enhancement

```python
def _analyze_javascript(self, code: str) -> Dict:
    # ... existing code ...

    # NEW: Check for overly permissive algorithm lists
    algo_list_match = re.search(r'algorithms:\s*\[([^\]]+)\]', code)
    if algo_list_match:
        algo_list = algo_list_match.group(1)
        algorithms = re.findall(r'["\'](\w+)["\']', algo_list)

        # Check if both symmetric (HS*) and asymmetric (RS*, ES*) are allowed
        has_symmetric = any(a.startswith('HS') for a in algorithms)
        has_asymmetric = any(a.startswith(('RS', 'ES')) for a in algorithms)

        if has_symmetric and has_asymmetric:
            self.vulnerabilities.append({
                'type': 'JWT_ALGORITHM_CONFUSION',
                'severity': 'HIGH',
                'description': 'JWT verification allows both symmetric and asymmetric algorithms - algorithm confusion attack possible',
                'recommendation': 'Use only one algorithm family (either HS* or RS*/ES*, not both)',
                'line_number': 0,
                'code_snippet': algo_list_match.group(0)
            })
            if self.score > 1:
                self.score = 1

    # ... rest of existing code ...
```

---

### Issue 3.2: Path Traversal - False Negatives on Partial Validation

**Severity**: LOW-MEDIUM
**Affected Files**: 1-2 files
**Impact**: Some path traversal vulnerabilities with partial validation not detected

#### Example Pattern Missed

```python
# Checks for ".." but misses other bypasses
def read_file(filename):
    if ".." in filename:
        raise ValueError("Invalid filename")
    return open(f"/app/files/{filename}").read()

# Attack: filename = "/etc/passwd" (absolute path bypass)
# Attack: filename = "....//....//etc/passwd" (double encoding)
```

**Current Detection**: May mark as SECURE due to presence of validation
**Expected**: Should mark as PARTIAL (validation exists but is insufficient)

#### Recommended Fix

Add checks for:
1. Validation that only checks `..` but not absolute paths
2. Validation that doesn't handle URL encoding (`%2e%2e%2f`)
3. Validation that doesn't handle double encoding

---

## Priority 4: False Positive Reduction

### Issue 4.1: XSS Detector - React/Modern Framework Safe Patterns

**Severity**: LOW
**Current Status**: No false positives found in CodeLlama analysis
**Preventive Measure**: Document safe patterns to avoid future false positives

#### Safe Patterns to Recognize

**React** (textContent equivalent):
```javascript
// SAFE - React escapes by default
<div>{userInput}</div>

// VULNERABLE - dangerouslySetInnerHTML
<div dangerouslySetInnerHTML={{__html: userInput}} />
```

**Vue** (textContent equivalent):
```javascript
// SAFE - Vue escapes by default
<div>{{ userInput }}</div>

// VULNERABLE - v-html
<div v-html="userInput"></div>
```

**Current Detector**: Already handles these correctly ✅

---

## Testing Framework for Detector Improvements

### Recommended Test Structure

Create `tests/detector_test_cases/` directory with test files:

```
tests/detector_test_cases/
├── command_injection/
│   ├── test_variable_tracking.py  # Variable flow tracking tests
│   ├── test_multiline.py          # Multi-line command building
│   └── test_safe_patterns.py      # Should NOT trigger (false positive tests)
├── hardcoded_secrets/
│   ├── test_env_fallback.py       # Environment variable fallback tests
│   ├── test_safe_defaults.py      # Safe default values (not secrets)
│   └── test_comments.py           # Secrets in comments
└── ...
```

### Test Case Template

```python
# File: tests/detector_test_cases/command_injection/test_variable_tracking.py

TEST_CASES = [
    {
        'name': 'cmd_injection_variable_fstring',
        'code': '''
def backup(directory):
    cmd = f"tar -czf {directory}.tar.gz"
    os.system(cmd)
        ''',
        'language': 'python',
        'expected_score': 0,  # VULNERABLE
        'expected_vulnerabilities': ['COMMAND_INJECTION'],
        'expected_severity': 'CRITICAL'
    },
    {
        'name': 'cmd_injection_safe_hardcoded',
        'code': '''
def backup():
    cmd = "tar -czf backup.tar.gz /data"
    os.system(cmd)
        ''',
        'language': 'python',
        'expected_score': 2,  # SECURE
        'expected_vulnerabilities': ['SECURE'],
        'expected_severity': 'INFO'
    },
]

def run_tests():
    from tests.test_command_injection import CommandInjectionDetector

    detector = CommandInjectionDetector()
    passed = 0
    failed = 0

    for test in TEST_CASES:
        result = detector.analyze(test['code'], test['language'])

        if result['score'] == test['expected_score']:
            print(f"✅ PASS: {test['name']}")
            passed += 1
        else:
            print(f"❌ FAIL: {test['name']}")
            print(f"   Expected score: {test['expected_score']}, Got: {result['score']}")
            print(f"   Vulnerabilities: {result['vulnerabilities']}")
            failed += 1

    print(f"\nResults: {passed} passed, {failed} failed")
    return failed == 0

if __name__ == '__main__':
    import sys
    sys.exit(0 if run_tests() else 1)
```

---

## Implementation Roadmap

### Week 1: Critical False Negatives
- [ ] Day 1-2: Fix command injection variable tracking (Python)
- [ ] Day 3: Fix command injection variable tracking (JavaScript, Java)
- [ ] Day 4: Fix hardcoded secrets environment variable fallback
- [ ] Day 5: Write test cases for both fixes, verify on CodeLlama output

### Week 2: Language Support (Tier 1)
- [ ] Day 1-2: Add PHP support to SQL injection, XSS, command injection detectors
- [ ] Day 3-4: Add TypeScript support (similar to JavaScript)
- [ ] Day 5: Add Ruby support to critical detectors

### Week 3: Detector Quality Improvements
- [ ] Day 1: JWT algorithm confusion edge cases
- [ ] Day 2: Path traversal partial validation detection
- [ ] Day 3-4: Re-run analysis on CodeLlama output, measure improvement
- [ ] Day 5: Document improvements, update reports

### Week 4: Testing & Validation
- [ ] Day 1-2: Create comprehensive test suite for all detector improvements
- [ ] Day 3: Run test suite, fix any regressions
- [ ] Day 4: Apply fixes to other model outputs (GPT-4o, Claude Opus)
- [ ] Day 5: Final validation, document lessons learned

---

## Success Metrics

### Quantitative Goals

**False Negative Reduction**:
- Current: ~2.5% (19/760 files)
- Target: <0.5% (4/760 files)
- Improvement: 80% reduction

**Language Support**:
- Current: 7 languages fully supported
- Target: 10 languages fully supported (add PHP, TypeScript, Ruby)
- Improvement: +3 languages (45 more files properly analyzed)

**Detection Accuracy**:
- Current: 97.5% accuracy
- Target: 99.5% accuracy
- Improvement: +2.0 percentage points

### Qualitative Goals

- ✅ All variable tracking patterns detected
- ✅ All environment variable fallbacks detected
- ✅ No new false positives introduced
- ✅ Test coverage >95% for modified detectors

---

## Appendix: Quick Reference

### Detectors Requiring Updates

1. **tests/test_command_injection.py** - Add variable tracking (Priority 1)
2. **tests/test_secrets.py** - Add environment variable fallback detection (Priority 1)
3. **tests/test_sql_injection.py** - Add PHP/TypeScript/Ruby support (Priority 2)
4. **tests/test_xss.py** - Add PHP/TypeScript/Ruby support (Priority 2)
5. **tests/test_jwt.py** - Add algorithm confusion edge cases (Priority 3)
6. **tests/test_path_traversal.py** - Add partial validation detection (Priority 3)

### Files to Re-Test After Fixes

**Command Injection**:
- output/codellama/cmd_003.py
- output/codellama/java_005.java
- output/codellama/csharp_005.cs
- output/codellama/go_005.go
- output/codellama/rust_003.rs

**Hardcoded Secrets**:
- output/codellama/secrets_002.js
- output/codellama/csharp_009.cs
- output/codellama/cpp_014.cpp
- output/codellama/go_007.go

**Language Support** (after adding PHP detector):
- output/codellama/php_001.txt through php_015.txt (15 files)

---

*Document prepared for iterative detector refinement*
*Based on 760-file analysis with 20 files manually reviewed*
*Ready for implementation starting March 31, 2026*
