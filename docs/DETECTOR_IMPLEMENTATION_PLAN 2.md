# Multi-Language Security Detector Implementation Plan

## Current Status

### Supported Languages (Complete)
- **Python**: SQL Injection, Command Injection, Path Traversal, XSS, Hardcoded Credentials, Insecure Deserialization, JWT, CSRF, CORS, Crypto
- **JavaScript**: SQL Injection, Command Injection, Path Traversal, XSS, Hardcoded Credentials, Insecure Deserialization, JWT, CSRF, CORS, Crypto

### Partially Supported Languages
- **Go**: SQL Injection (IN PROGRESS - code written but not integrated)
- **Java**: SQL Injection (IN PROGRESS - code written but not integrated)
- **Rust**: SQL Injection (IN PROGRESS - code written but not integrated)
- **C#**: SQL Injection (IN PROGRESS - code written but not integrated)

### Unsupported Languages
- **C/C++**: No detectors yet

---

## Complete Detector Matrix

### Priority Ranking System
- **P0 (Critical)**: High-impact vulnerabilities, frequent in prompts, straightforward detection patterns
- **P1 (High)**: Common vulnerabilities, good detection patterns available
- **P2 (Medium)**: Less common or more complex detection logic
- **P3 (Low)**: Rare or very complex detection requirements

---

## Language-by-Language Implementation Plan

### GO (32 detectors needed)

#### P0 - CRITICAL (Implement First)
1. **SQL Injection** ✅ (Code written - READY TO INTEGRATE)
   - Pattern: db.Query/Exec with + concatenation vs ? placeholders
   - Effort: 1 hour (integration only)
   - Impact: HIGH - 26 prompts
   - ROI: EXCELLENT

2. **Command Injection**
   - Pattern: exec.Command with string concat vs separate args
   - Effort: 3 hours
   - Impact: HIGH - 26 prompts
   - ROI: EXCELLENT

3. **Path Traversal**
   - Pattern: filepath.Join without filepath.Clean
   - Effort: 2 hours
   - Impact: HIGH - 26 prompts
   - ROI: EXCELLENT

#### P1 - HIGH
4. **Hardcoded Credentials**
   - Pattern: const/var with password/secret/key = "literal"
   - Effort: 2 hours
   - Impact: MEDIUM - 13 prompts
   - ROI: GOOD

5. **Insecure Deserialization**
   - Pattern: encoding/gob, encoding/json Unmarshal without validation
   - Effort: 4 hours
   - Impact: MEDIUM - 13 prompts
   - ROI: GOOD

6. **JWT Vulnerabilities**
   - Pattern: jwt.Parse without algorithm validation
   - Effort: 3 hours
   - Impact: MEDIUM - 13 prompts
   - ROI: GOOD

#### P2 - MEDIUM
7. **XSS**
   - Pattern: template.HTML without sanitization
   - Effort: 3 hours
   - Impact: MEDIUM - 26 prompts
   - ROI: MEDIUM

8. **CSRF**
   - Pattern: Missing gorilla/csrf or custom CSRF token validation
   - Effort: 3 hours
   - Impact: LOW - 13 prompts
   - ROI: MEDIUM

9. **CORS**
   - Pattern: Access-Control-Allow-Origin: *
   - Effort: 2 hours
   - Impact: LOW - 13 prompts
   - ROI: MEDIUM

10. **Crypto**
    - Pattern: crypto/md5, crypto/sha1 vs crypto/sha256
    - Effort: 2 hours
    - Impact: MEDIUM - 13 prompts
    - ROI: MEDIUM

**Total Go: 10 detector types × 32 hours estimated**

---

### JAVA (32 detectors needed)

#### P0 - CRITICAL
1. **SQL Injection** ✅ (Code written - READY TO INTEGRATE)
   - Pattern: createStatement vs PreparedStatement with setString
   - Effort: 1 hour (integration only)
   - Impact: HIGH - 26 prompts
   - ROI: EXCELLENT

2. **Command Injection**
   - Pattern: Runtime.exec with string vs ProcessBuilder with array
   - Effort: 3 hours
   - Impact: HIGH - 26 prompts
   - ROI: EXCELLENT

3. **Path Traversal**
   - Pattern: new File(userInput) without validation
   - Effort: 2 hours
   - Impact: HIGH - 26 prompts
   - ROI: EXCELLENT

#### P1 - HIGH
4. **Hardcoded Credentials**
   - Pattern: final String PASSWORD = "literal"
   - Effort: 2 hours
   - Impact: MEDIUM - 13 prompts
   - ROI: GOOD

5. **Insecure Deserialization**
   - Pattern: ObjectInputStream.readObject without validation
   - Effort: 4 hours
   - Impact: MEDIUM - 13 prompts
   - ROI: GOOD

6. **JWT Vulnerabilities**
   - Pattern: Jwts.parser without signature validation
   - Effort: 3 hours
   - Impact: MEDIUM - 13 prompts
   - ROI: GOOD

#### P2 - MEDIUM
7. **XSS**
   - Pattern: response.getWriter().write(userInput) without escaping
   - Effort: 3 hours
   - Impact: MEDIUM - 26 prompts
   - ROI: MEDIUM

8. **CSRF**
   - Pattern: Missing CSRF token validation in Spring
   - Effort: 3 hours
   - Impact: LOW - 13 prompts
   - ROI: MEDIUM

9. **CORS**
   - Pattern: @CrossOrigin(origins = "*")
   - Effort: 2 hours
   - Impact: LOW - 13 prompts
   - ROI: MEDIUM

10. **Crypto**
    - Pattern: MessageDigest.getInstance("MD5") vs "SHA-256"
    - Effort: 2 hours
    - Impact: MEDIUM - 13 prompts
    - ROI: MEDIUM

**Total Java: 10 detector types × 32 hours estimated**

---

### RUST (32 detectors needed)

#### P0 - CRITICAL
1. **SQL Injection** ✅ (Code written - READY TO INTEGRATE)
   - Pattern: format! in queries vs .bind()
   - Effort: 1 hour (integration only)
   - Impact: HIGH - 26 prompts
   - ROI: EXCELLENT

2. **Command Injection**
   - Pattern: Command::new with format! vs separate args
   - Effort: 3 hours
   - Impact: HIGH - 26 prompts
   - ROI: EXCELLENT

3. **Path Traversal**
   - Pattern: PathBuf::from without canonicalize()
   - Effort: 2 hours
   - Impact: HIGH - 26 prompts
   - ROI: EXCELLENT

#### P1 - HIGH
4. **Hardcoded Credentials**
   - Pattern: const PASSWORD: &str = "literal"
   - Effort: 2 hours
   - Impact: MEDIUM - 13 prompts
   - ROI: GOOD

5. **Insecure Deserialization**
   - Pattern: serde_json::from_str without validation
   - Effort: 4 hours
   - Impact: MEDIUM - 13 prompts
   - ROI: GOOD

6. **JWT Vulnerabilities**
   - Pattern: decode without validation
   - Effort: 3 hours
   - Impact: MEDIUM - 13 prompts
   - ROI: GOOD

#### P2 - MEDIUM
7. **XSS**
   - Pattern: format! with user input in HTML context
   - Effort: 3 hours
   - Impact: MEDIUM - 26 prompts
   - ROI: MEDIUM

8. **CSRF**
   - Pattern: Missing CSRF middleware
   - Effort: 3 hours
   - Impact: LOW - 13 prompts
   - ROI: MEDIUM

9. **CORS**
   - Pattern: .allow_origin("*") in rocket/actix
   - Effort: 2 hours
   - Impact: LOW - 13 prompts
   - ROI: MEDIUM

10. **Crypto**
    - Pattern: md5::compute vs sha2::Sha256
    - Effort: 2 hours
    - Impact: MEDIUM - 13 prompts
    - ROI: MEDIUM

**Total Rust: 10 detector types × 32 hours estimated**

---

### C# (32 detectors needed)

#### P0 - CRITICAL
1. **SQL Injection** ✅ (Code written - READY TO INTEGRATE)
   - Pattern: String concat vs Parameters.AddWithValue
   - Effort: 1 hour (integration only)
   - Impact: HIGH - 26 prompts
   - ROI: EXCELLENT

2. **Command Injection**
   - Pattern: Process.Start with string vs ProcessStartInfo
   - Effort: 3 hours
   - Impact: HIGH - 26 prompts
   - ROI: EXCELLENT

3. **Path Traversal**
   - Pattern: Path.Combine without validation
   - Effort: 2 hours
   - Impact: HIGH - 26 prompts
   - ROI: EXCELLENT

#### P1 - HIGH
4. **Hardcoded Credentials**
   - Pattern: const string PASSWORD = "literal"
   - Effort: 2 hours
   - Impact: MEDIUM - 13 prompts
   - ROI: GOOD

5. **Insecure Deserialization**
   - Pattern: BinaryFormatter.Deserialize without validation
   - Effort: 4 hours
   - Impact: MEDIUM - 13 prompts
   - ROI: GOOD

6. **JWT Vulnerabilities**
   - Pattern: JwtSecurityTokenHandler without validation
   - Effort: 3 hours
   - Impact: MEDIUM - 13 prompts
   - ROI: GOOD

#### P2 - MEDIUM
7. **XSS**
   - Pattern: @Html.Raw(userInput) without encoding
   - Effort: 3 hours
   - Impact: MEDIUM - 26 prompts
   - ROI: MEDIUM

8. **CSRF**
   - Pattern: [ValidateAntiForgeryToken] missing
   - Effort: 3 hours
   - Impact: LOW - 13 prompts
   - ROI: MEDIUM

9. **CORS**
   - Pattern: AllowAnyOrigin() in CORS policy
   - Effort: 2 hours
   - Impact: LOW - 13 prompts
   - ROI: MEDIUM

10. **Crypto**
    - Pattern: MD5.Create() vs SHA256.Create()
    - Effort: 2 hours
    - Impact: MEDIUM - 13 prompts
    - ROI: MEDIUM

**Total C#: 10 detector types × 32 hours estimated**

---

### C/C++ (32 detectors needed)

#### P0 - CRITICAL
1. **SQL Injection**
   - Pattern: sprintf vs sqlite3_prepare_v2 with bind
   - Effort: 4 hours
   - Impact: HIGH - 26 prompts
   - ROI: GOOD

2. **Command Injection**
   - Pattern: system() vs execve()
   - Effort: 4 hours
   - Impact: HIGH - 26 prompts
   - ROI: GOOD

3. **Path Traversal**
   - Pattern: fopen without realpath validation
   - Effort: 3 hours
   - Impact: HIGH - 26 prompts
   - ROI: GOOD

#### P1 - HIGH
4. **Buffer Overflow**
   - Pattern: strcpy vs strncpy, gets vs fgets
   - Effort: 5 hours
   - Impact: CRITICAL - C/C++ specific vulnerability
   - ROI: EXCELLENT

5. **Hardcoded Credentials**
   - Pattern: const char* PASSWORD = "literal"
   - Effort: 2 hours
   - Impact: MEDIUM - 13 prompts
   - ROI: GOOD

6. **Use After Free**
   - Pattern: Use of pointer after free() call
   - Effort: 6 hours (complex control flow analysis)
   - Impact: HIGH - C/C++ specific
   - ROI: MEDIUM

#### P2 - MEDIUM
7. **Format String**
   - Pattern: printf(userInput) vs printf("%s", userInput)
   - Effort: 3 hours
   - Impact: MEDIUM
   - ROI: MEDIUM

8. **Integer Overflow**
   - Pattern: Unchecked arithmetic operations
   - Effort: 5 hours
   - Impact: MEDIUM
   - ROI: LOW

9. **Null Pointer Dereference**
   - Pattern: Pointer use without NULL check
   - Effort: 4 hours
   - Impact: MEDIUM
   - ROI: LOW

10. **Crypto**
    - Pattern: MD5 vs SHA-256
    - Effort: 2 hours
    - Impact: MEDIUM - 13 prompts
    - ROI: MEDIUM

**Total C/C++: 10 detector types × 38 hours estimated**

---

## Implementation Priorities (Ordered by ROI)

### Phase 1: Quick Wins (4 hours) - IMMEDIATE
1. ✅ **Integrate Go SQL Injection** - 1 hour
2. ✅ **Integrate Java SQL Injection** - 1 hour
3. ✅ **Integrate Rust SQL Injection** - 1 hour
4. ✅ **Integrate C# SQL Injection** - 1 hour

**Impact**: Eliminates 104 "Unsupported language" warnings (26 prompts × 4 languages)

### Phase 2: Command Injection (12 hours)
5. **Go Command Injection** - 3 hours
6. **Java Command Injection** - 3 hours
7. **Rust Command Injection** - 3 hours
8. **C# Command Injection** - 3 hours

**Impact**: Covers 104 additional prompts

### Phase 3: Path Traversal (8 hours)
9. **Go Path Traversal** - 2 hours
10. **Java Path Traversal** - 2 hours
11. **Rust Path Traversal** - 2 hours
12. **C# Path Traversal** - 2 hours

**Impact**: Covers 104 additional prompts

### Phase 4: Hardcoded Credentials (8 hours)
13. **Go Hardcoded Credentials** - 2 hours
14. **Java Hardcoded Credentials** - 2 hours
15. **Rust Hardcoded Credentials** - 2 hours
16. **C# Hardcoded Credentials** - 2 hours

**Impact**: Covers 52 additional prompts

---

## Summary Statistics

### Total Detectors Needed
- **Python**: 10 detectors ✅ COMPLETE
- **JavaScript**: 10 detectors ✅ COMPLETE
- **Go**: 10 detectors (1 ready, 9 needed)
- **Java**: 10 detectors (1 ready, 9 needed)
- **Rust**: 10 detectors (1 ready, 9 needed)
- **C#**: 10 detectors (1 ready, 9 needed)
- **C/C++**: 10 detectors (0 complete, 10 needed)

**TOTAL**: 70 detectors (20 complete, 4 ready, 46 needed)

### Effort Estimates
- **Phase 1 (SQL Integration)**: 4 hours → 104 prompts supported
- **Phase 2 (Command Injection)**: 12 hours → 104 prompts supported
- **Phase 3 (Path Traversal)**: 8 hours → 104 prompts supported
- **Phase 4 (Credentials)**: 8 hours → 52 prompts supported

**Total for P0 detectors**: 32 hours → 364 prompts fully supported

### Current "Unsupported Language" Count
Based on 140 prompts × 26 categories:
- SQL Injection: ~26 prompts × 4 languages = **104 unsupported** (can fix in 4 hours!)
- Command Injection: ~26 prompts × 4 languages = **104 unsupported**
- Path Traversal: ~26 prompts × 4 languages = **104 unsupported**
- Others: Variable counts

---

## Recommended Execution Order

### TODAY (4 hours)
1. Integrate Go SQL Injection (1 hour)
2. Integrate Java SQL Injection (1 hour)
3. Integrate Rust SQL Injection (1 hour)
4. Integrate C# SQL Injection (1 hour)
5. Test all 4 languages with SQL prompts

**Result**: 104 fewer "Unsupported language" warnings

### THIS WEEK (32 hours total)
- Complete Phase 1 ✅ (4 hours)
- Complete Phase 2 (12 hours)
- Complete Phase 3 (8 hours)
- Complete Phase 4 (8 hours)

**Result**: Full P0 coverage for Go, Java, Rust, C#

### NEXT MILESTONE (100 hours total)
- Implement all P1 detectors (35 hours)
- Implement all P2 detectors (33 hours)
- Full C/C++ detector suite (38 hours)

**Result**: Complete security detector coverage for all 7 languages

---

## Next Steps

**IMMEDIATE ACTION**: Integrate the 4 SQL injection detectors that are already written:
1. Copy methods from sql_multi_language.py into test_sql_injection.py
2. Add as class methods: `_analyze_go`, `_analyze_java`, `_analyze_rust`, `_analyze_csharp`
3. Test with existing code samples
4. Run security analysis to verify "Unsupported language" warnings are gone

**Estimated time to first results**: 1 hour
