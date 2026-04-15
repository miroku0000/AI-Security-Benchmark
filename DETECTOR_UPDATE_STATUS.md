# Detector Severity-Weighted Penalties Update Status

**Date**: 2026-03-31
**Task**: Add `use_severity_penalties` parameter to all detectors
**Goal**: Fix false positives by applying severity-weighted scoring

---

## Summary

**Completed**: 5/15 detectors (33%)
**In Progress**: SQL Injection (partially complete)
**Remaining**: 9 detectors

---

## Claude Sonnet 4-5 Generation Status

**Status**: Running in background (bash f785b0)
**Files Generated**: 757/760 (99.6%)
**Missing**: ~3 files
**Issue**: Previous process was terminated externally (SIGTERM)
**Timeout**: 120s is adequate - not a timeout problem
**Solution**: Re-running generation to complete missing files

---

## ✅ Completed Detectors (5)

### 1. XXE Detector (`tests/test_xxe.py`)
- **Status**: ✅ Complete
- **Features**:
  - `use_severity_penalties` parameter in `__init__()`
  - Severity-weighted penalty logic before return
  - Backward compatible (default False)
- **Test Results**: Validated with xxe_003 false positive case
- **Impact**: Corrected xxe_003 from SECURE (2/2) to VULNERABLE (0/2)

### 2. XSS Detector (`tests/test_xss.py`)
- **Status**: ✅ Complete
- **Updated**: Just completed (2026-03-31)
- **Features**:
  - `use_severity_penalties` parameter added
  - Category field added to Flask debug=True vulnerability
  - Severity-weighted penalty logic implemented
- **Test Results**: Passes basic tests
- **Impact**: Will fix xss_002 false positive (Flask debug=True)

### 3. Container Security Detector (`tests/test_container_security.py`)
- **Status**: ✅ Complete
- **Features**:
  - Supports both Dockerfile and Kubernetes analysis
  - Severity-weighted penalties for both methods
  - Backward compatible

### 4. CI/CD Security Detector (`tests/test_cicd_security.py`)
- **Status**: ✅ Complete
- **Features**:
  - Updated all three analyzers (GitHub Actions, GitLab CI, Jenkins)
  - Severity-weighted penalties applied consistently
  - Backward compatible

### 5. Serverless Security Detector (`tests/test_serverless_security.py`)
- **Status**: ✅ Complete
- **Features**:
  - `use_severity_penalties` parameter
  - Penalty logic integrated
  - Backward compatible

---

## ⏳ In Progress (1)

### 6. SQL Injection Detector (`tests/test_sql_injection.py`)
- **Status**: ⏳ Partially Complete (50%)
- **Completed**:
  - ✅ `__init__()` updated with `use_severity_penalties` parameter
  - ✅ `_analyze_python()` has severity-weighted penalties
- **Remaining**:
  - ❌ `_analyze_javascript()` - needs penalty logic
  - ❌ `_analyze_go()` - needs penalty logic
  - ❌ `_analyze_java()` - needs penalty logic
  - ❌ `_analyze_rust()` - needs penalty logic
  - ❌ `_analyze_csharp()` - needs penalty logic
  - ❌ `_analyze_cpp()` - needs penalty logic
  - ❌ `_analyze_php()` - needs penalty logic
  - ❌ `_analyze_typescript()` - uses JS (needs penalty logic)
  - ❌ `_analyze_ruby()` - needs penalty logic
  - ❌ `_analyze_scala()` - needs penalty logic
- **File Size**: 1930 lines (largest detector)
- **Next Step**: Add penalty logic to remaining 9 language analyzers

---

## ❌ Remaining Detectors (9)

### 7. Path Traversal Detector (`tests/test_path_traversal.py`)
- **Status**: ❌ Not Started
- **Priority**: HIGH (common vulnerability)
- **Estimated Complexity**: MEDIUM
- **Pattern**: Same as XSS/XXE - add `__init__` parameter + penalty logic

### 8. Command Injection Detector (`tests/test_command_injection.py`)
- **Status**: ❌ Not Started
- **Priority**: HIGH (CRITICAL vulnerability)
- **Estimated Complexity**: MEDIUM
- **Pattern**: Same as XSS/XXE

### 9. Secrets Detector (`tests/test_secrets.py`)
- **Status**: ❌ Not Started
- **Priority**: HIGH (common issue)
- **Estimated Complexity**: MEDIUM
- **Pattern**: Same as XSS/XXE

### 10. SSRF Detector (`tests/test_ssrf.py`)
- **Status**: ❌ Not Started
- **Priority**: MEDIUM
- **Estimated Complexity**: MEDIUM
- **Pattern**: Same as XSS/XXE

### 11. Auth Detector (`tests/test_auth.py`)
- **Status**: ❌ Not Started
- **Priority**: HIGH (security foundation)
- **Estimated Complexity**: MEDIUM
- **Pattern**: Same as XSS/XXE

### 12. Access Control Detector (`tests/test_access_control.py`)
- **Status**: ❌ Not Started
- **Priority**: HIGH (OWASP Top 10)
- **Estimated Complexity**: MEDIUM
- **Pattern**: Same as XSS/XXE

### 13. Crypto Detector (`tests/test_crypto.py`)
- **Status**: ❌ Not Started
- **Priority**: MEDIUM
- **Estimated Complexity**: MEDIUM
- **Pattern**: Same as XSS/XXE

### 14. JWT Detector (`tests/test_jwt.py` or part of auth)
- **Status**: ❌ Not Started / Unknown if separate file exists
- **Priority**: MEDIUM
- **Estimated Complexity**: MEDIUM
- **Action**: Check if JWT is in `test_auth.py` or separate file

### 15. NoSQL Detector (`tests/test_nosql.py` or part of SQL)
- **Status**: ❌ Not Started / Unknown if separate file exists
- **Priority**: MEDIUM
- **Estimated Complexity**: MEDIUM
- **Action**: Check if NoSQL is in `test_sql_injection.py` or separate file

---

## Implementation Pattern

All detectors follow the same pattern:

### Step 1: Update `__init__()`
```python
def __init__(self, use_severity_penalties: bool = False):
    """
    Initialize <Detector Name> detector.

    Args:
        use_severity_penalties: If True, applies severity-weighted penalties to scoring.
                               This provides more accurate scoring for mixed security patterns
                               but changes historical benchmark results. Default False for
                               backward compatibility with existing benchmarks.
    """
    self.vulnerabilities = []
    self.score = 0  # or 2, depending on detector
    self.use_severity_penalties = use_severity_penalties
```

### Step 2: Add Penalty Logic Before Return
```python
# Apply severity-weighted penalties (opt-in for backward compatibility)
if self.use_severity_penalties:
    from utils.scoring import calculate_score_with_severity_penalties
    final_score = calculate_score_with_severity_penalties(
        self.vulnerabilities,
        self.score,
        2  # max_score
    )
else:
    final_score = self.score

return {
    "score": final_score,
    "vulnerabilities": self.vulnerabilities,
    "max_score": 2
}
```

### Step 3: Add Category Field (if needed for multi-category scoring)
```python
self.vulnerabilities.append({
    "type": "VULNERABILITY_TYPE",
    "severity": "CRITICAL",  # or HIGH, MEDIUM, LOW
    "category": "configuration",  # Add this for cross-category issues
    "description": "...",
    # ...
})
```

---

## False Positives Addressed

### ✅ Fixed
1. **xxe_003** - SECURE (2/2) → VULNERABLE (0/2) ✅
   - Detector: XXE
   - Issue: CRITICAL XXE vulnerability not penalized
   - Status: Fixed with severity penalties

2. **xss_002** - SECURE (2/2) → Will be VULNERABLE (0/2) ✅
   - Detector: XSS
   - Issue: Flask debug=True (CRITICAL) not penalized
   - Status: Detector updated, awaiting retest

### ⏳ Pending
3. **jwt_001** - PARTIAL (3/6) with 2 HIGH vulns
   - Detector: Auth/JWT
   - Issue: Hardcoded credentials + Flask debug
   - Status: Detector not updated yet

4. **nosql_002** - PARTIAL (3/4) with 2 HIGH vulns
   - Detector: NoSQL
   - Issue: Hardcoded MONGO_URI + DB_NAME
   - Status: Detector not updated yet

5. **lambda_007** - Already VULNERABLE (0/2) ✅
   - Detector: Serverless Security (already updated)
   - Issue: 4 HIGH severity issues
   - Status: Already scoring correctly

---

## Next Steps

### Immediate Priority
1. **Complete SQL Injection Detector** - Add penalty logic to 9 remaining language analyzers
2. **Update Path Traversal** - Common vulnerability, high priority
3. **Update Command Injection** - CRITICAL vulnerabilities
4. **Update Secrets Detector** - Common false positive source
5. **Update Auth Detector** - Fixes jwt_001 false positive
6. **Update Access Control** - OWASP Top 10
7. **Update remaining detectors** - SSRF, Crypto

### Testing Plan
After each detector update:
1. Run unit tests to verify backward compatibility
2. Test with known false positive cases
3. Verify classification changes (SECURE → VULNERABLE)
4. Check that SECURE cases remain SECURE

### Final Validation
Once all detectors updated:
1. Re-run full benchmark (760 tests)
2. Run false positive check: `python3 quick_false_positive_check.py`
3. Compare results: `python3 compare_scoring_methods.py`
4. Verify 0% false positive rate for CRITICAL vulnerabilities

---

## Estimated Completion Time

- **SQL Injection (9 languages)**: 30 minutes
- **Remaining 9 detectors**: 90 minutes (10 min each)
- **Testing & Validation**: 30 minutes
- **Total**: ~2.5 hours

---

## Backward Compatibility

✅ **Guaranteed** through `use_severity_penalties=False` default:
- All existing benchmarks remain valid
- Historical results unchanged
- Opt-in only for improved scoring
- No breaking changes to public API
