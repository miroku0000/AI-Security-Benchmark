# Detector Iterative Refinement - Priority Analysis

**Date**: 2026-03-31
**Analysis**: CodeLlama benchmark results after Priority 1-4 improvements
**Goal**: Identify highest-impact detector improvements for next iteration

---

## Executive Summary

After implementing Priority 1-4 detector improvements, we achieved:
- ✅ Command Injection: +13.0% (17.4% → 30.4%)
- ✅ Hardcoded Secrets: +8.7% (26.1% → 34.8%)
- ✅ SQL Injection: +7.4% (18.5% → 25.9%)
- ✅ Path Traversal: +10.5% (21.1% → 31.6%)
- ✅ XSS: +20.0% (0% → 20%)

**Next Iteration Focus**: Categories with 75%+ vulnerability rates (detectors missing or incomplete)

---

## Priority 1: Critical Coverage Gaps (100% Vulnerable Rate)

These categories have **NO effective detection** currently:

### 1.1 Insecure File Upload (7/7 cases = 100% vulnerable)

**Impact**: High - File upload vulnerabilities enable:
- Remote code execution via uploaded scripts
- Path traversal attacks
- Server-side code injection

**Missing Detection Patterns**:
- File extension validation bypass (double extensions: `.php.jpg`)
- MIME type validation bypass
- Missing file size limits
- Unrestricted upload directories
- Lack of filename sanitization
- Missing virus/malware scanning

**Implementation Priority**: **CRITICAL**
**Estimated Impact**: +100% detection (0% → 100%)

---

### 1.2 Open Redirect (4/4 cases = 100% vulnerable)

**Impact**: Medium - Open redirect vulnerabilities enable:
- Phishing attacks (trusted domain → malicious site)
- OAuth token theft
- SSRF via redirects

**Missing Detection Patterns**:
- Unvalidated redirect parameters: `redirect_url=`, `next=`, `return_to=`
- Missing URL whitelist validation
- Missing domain validation in redirect logic
- JavaScript-based redirects: `window.location = user_input`
- HTTP header redirects without validation: `Location: ${user_url}`

**Implementation Priority**: **CRITICAL**
**Estimated Impact**: +100% detection (0% → 100%)

---

### 1.3 Business Logic Flaws (3/3 cases = 100% vulnerable)

**Impact**: High - Business logic flaws enable:
- Price manipulation (e.g., negative quantity discounts)
- Workflow bypass (skip payment steps)
- Privilege escalation via logic errors

**Missing Detection Patterns**:
- Missing quantity validation (negative numbers)
- Missing price integrity checks
- Workflow sequence violations
- Race conditions in state transitions
- Missing authentication in critical business operations

**Implementation Priority**: **HIGH**
**Estimated Impact**: Partial (~50-70% detection) - Business logic is hard to detect with static analysis

---

## Priority 2: High Vulnerability Rate (75-92%)

### 2.1 SSRF (Server-Side Request Forgery) - 92.3% vulnerable (12/13 cases)

**Current Status**: 1/13 secure - minimal detection exists

**Missing Detection Patterns**:
- HTTP requests with user-controlled URLs
- `requests.get(user_url)`, `fetch(user_input)`, `curl(user_url)`
- Missing allowlist validation for URLs
- DNS rebinding vulnerabilities
- URL parsing bypasses (`http://attacker.com@internal.host`)
- Cloud metadata service access (`http://169.254.169.254/`)

**Implementation Priority**: **HIGH**
**Estimated Impact**: +80% detection (7.7% → ~80%)

---

### 2.2 Container Security - 90.0% vulnerable (27/30 cases)

**Current Status**: 2/30 secure - no dedicated detector

**Missing Detection Patterns**:
- Running containers as root: `USER root` in Dockerfile
- Privileged containers: `--privileged` flag
- Host path mounts: `volumes: ["/:/host"]`
- Missing resource limits: no `limits.memory` or `limits.cpu`
- Exposed Docker socket: `/var/run/docker.sock` mount
- Hardcoded secrets in Dockerfiles
- Using `latest` tag (no version pinning)

**Implementation Priority**: **HIGH**
**Estimated Impact**: +70% detection (6.7% → ~75%)

---

### 2.3 Race Condition - 84.6% vulnerable (11/13 cases)

**Current Status**: 2/13 secure - basic detection exists

**Missing Detection Patterns**:
- TOCTOU (Time-of-Check-Time-of-Use) in file operations
- Missing locking in database updates
- Non-atomic increment operations
- Missing transaction isolation levels
- File permission checks without proper locking
- Concurrent access to shared resources without synchronization

**Implementation Priority**: **MEDIUM**
**Estimated Impact**: +50% detection (15.4% → ~65%)

---

## Priority 3: Language Support Gaps

### 3.1 XSS - Missing Language Support

**Current Status**: 80% secure rate for supported languages, but 3 unsupported:
- Scala (scala_003)
- Perl (perl_008)
- Elixir (elixir_003)

**Implementation**: Add XSS detection for these 3 languages

**Estimated Impact**: +20% XSS detection (20% → 40%)

---

## Recommended Implementation Order

### Phase 1: Critical Gaps (Weeks 1-2)
1. **Insecure File Upload Detector** - New detector file: `tests/test_file_upload.py`
2. **Open Redirect Detector** - New detector file: `tests/test_open_redirect.py`
3. **SSRF Detector Enhancement** - Enhance existing `tests/test_ssrf.py`

**Expected Results**:
- insecure_upload: 0% → 80%+
- open_redirect: 0% → 90%+
- SSRF: 7.7% → 70%+

### Phase 2: High-Impact (Weeks 3-4)
4. **Container Security Detector** - New detector file: `tests/test_container_security.py`
5. **Business Logic Detector** - New detector file: `tests/test_business_logic.py`
6. **Race Condition Enhancement** - Enhance existing `tests/test_race_condition.py`

**Expected Results**:
- container_security: 6.7% → 60%+
- business_logic_flaw: 0% → 50%+
- race_condition: 15.4% → 60%+

### Phase 3: Language Coverage (Week 5)
7. **XSS Language Support** - Add Scala, Perl, Elixir to `tests/test_xss.py`

**Expected Results**:
- XSS: 20% → 40%

---

## Detection Pattern Templates

### File Upload Detector Template
```python
class FileUploadDetector:
    """Detects insecure file upload vulnerabilities."""

    def analyze(self, code: str, language: str) -> Dict:
        # Pattern 1: Missing extension validation
        # Pattern 2: Missing MIME type validation
        # Pattern 3: Unrestricted upload directory
        # Pattern 4: Missing filename sanitization
        # Pattern 5: No file size limits
```

### Open Redirect Detector Template
```python
class OpenRedirectDetector:
    """Detects open redirect vulnerabilities."""

    def analyze(self, code: str, language: str) -> Dict:
        # Pattern 1: Unvalidated redirect parameters
        # Pattern 2: Missing URL whitelist
        # Pattern 3: JavaScript location redirects
        # Pattern 4: HTTP Location header with user input
```

### SSRF Detector Enhancement
```python
class SSRFDetector:
    """Detects SSRF vulnerabilities."""

    def analyze(self, code: str, language: str) -> Dict:
        # ENHANCE: Add URL allowlist validation check
        # ENHANCE: Add cloud metadata URL detection
        # ENHANCE: Add DNS rebinding pattern detection
        # ENHANCE: Track URL construction from user input
```

---

## Success Metrics

**Overall Benchmark Improvement Target**: +15% (64.3% → ~79%)

**Category-Specific Targets**:
| Category | Current | Target | Improvement |
|----------|---------|--------|-------------|
| insecure_upload | 0.0% | 80.0% | +80.0% |
| open_redirect | 0.0% | 90.0% | +90.0% |
| SSRF | 7.7% | 70.0% | +62.3% |
| container_security | 6.7% | 60.0% | +53.3% |
| business_logic_flaw | 0.0% | 50.0% | +50.0% |
| race_condition | 15.4% | 60.0% | +44.6% |
| XSS | 20.0% | 40.0% | +20.0% |

---

## Next Steps

1. **Review and approve priority order** with team
2. **Start Phase 1** with file upload detector implementation
3. **Create test cases** for each new detector (10+ test cases per detector)
4. **Implement detectors** following existing patterns in `tests/` directory
5. **Run test suites** to verify 100% pass rate
6. **Re-run CodeLlama benchmark** with enhanced detectors
7. **Compare results** and document improvements
8. **Iterate** for Phase 2 and Phase 3

---

**Generated**: 2026-03-31
**Generated with**: [Claude Code](https://claude.com/claude-code)
**Report by**: Claude (Sonnet 4.5)
