# Unsupported Languages - Strategic Remediation Plan

**Date**: 2026-03-31
**Critical Issue**: 112 test cases returning "UNSUPPORTED" across 24 languages
**User Requirement**: "We should never have any Unsupported Language"

---

## Executive Summary

**Total Unsupported Cases**: 112/760 (14.7% of all test cases)

**Languages Requiring Support** (by number of categories):
1. Scala - 10 categories
2. Elixir - 9 categories
3. Lua - 9 categories
4. Perl - 7 categories
5. Bash - 4 categories
6. PHP - 6 categories (gaps in existing support)
7. Java - 6 categories (gaps in existing support)
8. C# - 4 categories (gaps in existing support)

---

## Phase 1: High-Volume Languages (Scala, Elixir, Lua, Perl)

### Priority 1A: Scala Support (10 categories, 10 cases)

**Categories**:
- SQL Injection (2 cases): `scala_001`, `scala_002`
- XSS (1 case): `scala_003`
- Command Injection (1 case): `scala_004`
- Insecure Deserialization (1 case): `scala_005`
- Path Traversal (1 case): `scala_006`
- Hardcoded Secrets (1 case): `scala_007`
- SSRF (1 case): `scala_008`
- Broken Access Control (1 case): `scala_009`
- Race Condition (1 case): `scala_010`
- XXE (1 case): `scala_012`

**Implementation Strategy**: Add Scala patterns to existing detectors
- SQL: `executeQuery()`, Play Framework `anorm` SQL interpolation
- XSS: Twirl templates, Play Framework HTML rendering
- Command Injection: `sys.process.Process`, `Runtime.getRuntime.exec()`
- Secrets: Scala config files, `typesafe.config`

---

### Priority 1B: Elixir Support (9 categories, 9 cases)

**Categories**:
- SQL Injection (2 cases): `elixir_001`, `elixir_002`
- XSS (1 case): `elixir_003`
- Command Injection (1 case): `elixir_004`
- Insecure Deserialization (1 case): `elixir_005`
- Race Condition (1 case): `elixir_006`
- SSRF (1 case): `elixir_007`
- Broken Access Control (1 case): `elixir_008`
- Hardcoded Secrets (1 case): `elixir_009`
- XXE (1 case): `elixir_010`

**Implementation Strategy**: Add Elixir/Phoenix patterns
- SQL: `Ecto.Query` raw SQL, `Repo.query()`
- XSS: Phoenix templates (EEx), `raw()` function
- Command Injection: `System.cmd()`, `:os.cmd()`
- Secrets: Application config, Mix environment

---

### Priority 1C: Lua Support (9 categories, 9 cases)

**Categories**:
- Command Injection (1 case): `lua_001`
- SQL Injection (1 case): `lua_003`
- SSRF (1 case): `lua_004`
- Path Traversal (1 case): `lua_005`
- NoSQL Injection (1 case): `lua_006`
- Race Condition (1 case): `lua_007`
- Hardcoded Secrets (1 case): `lua_008`
- XXE (1 case): `lua_010`
- Insecure Deserialization (1 case): `lua_012`

**Implementation Strategy**: Add Lua/OpenResty/NGINX patterns
- SQL: `luasql` library patterns
- Command Injection: `os.execute()`, `io.popen()`
- SSRF: `http` library, `ngx.location.capture()`
- Secrets: Lua config files, environment variables

---

### Priority 1D: Perl Support (7 categories, 7 cases)

**Categories**:
- SQL Injection (1 case): `perl_001`
- Command Injection (1 case): `perl_002`
- Path Traversal (1 case): `perl_003`
- Hardcoded Secrets (1 case): `perl_006`
- XSS (1 case): `perl_008`
- Open Redirect (1 case): `perl_009`
- Insecure Deserialization (1 case): `perl_010`

**Implementation Strategy**: Add Perl/CGI patterns
- SQL: DBI `do()`, `execute()` without placeholders
- Command Injection: backticks, `system()`, `exec()`
- XSS: CGI `print` statements with user input
- Secrets: Perl scripts with hardcoded credentials

---

## Phase 2: Bash Scripting Support (4 categories, 9 cases)

### Priority 2A: Bash Support

**Categories**:
- Command Injection (5 cases): `bash_001` through `bash_004`, `bash_010`
- Path Traversal (2 cases): `bash_005`, `bash_006`
- Hardcoded Secrets (2 cases): `bash_007`, `bash_008`
- Race Condition (1 case): `bash_009`

**Implementation Strategy**: Add Bash shell script patterns
- Command Injection: `eval`, `$()`, backticks, unquoted variables
- Path Traversal: File operations with `${}` without validation
- Secrets: Hardcoded passwords/keys in shell scripts
- Race Condition: TOCTOU in file checks without `flock`

---

## Phase 3: Mobile Languages (Swift, Kotlin, Dart)

### Priority 3A: Swift Support (3 categories, 3 cases)

**Categories**:
- Hardcoded Secrets (1 case): `mobile_061`
- Information Disclosure (1 case): `mobile_056`
- Insecure Data Storage (1 case): `mobile_010`

**Implementation Strategy**: Add iOS/Swift patterns
- Secrets: Hardcoded API keys in Swift code
- Information Disclosure: NSLog leaking sensitive data
- Data Storage: Unencrypted UserDefaults, Keychain misuse

---

### Priority 3B: Kotlin Support (3 categories, 3 cases)

**Categories**:
- Hardcoded Secrets (1 case): `mobile_062`
- Information Disclosure (1 case): `mobile_057`
- Insecure Data Storage (1 case): `mobile_017`

**Implementation Strategy**: Add Android/Kotlin patterns
- Secrets: Hardcoded secrets in Kotlin companion objects
- Information Disclosure: Log.d/Log.e leaking sensitive data
- Data Storage: SharedPreferences without encryption

---

### Priority 3C: Dart/Flutter Support (4 categories, 4 cases)

**Categories**:
- Cleartext Network Traffic (1 case): `mobile_037`
- Hardcoded Secrets (1 case): `mobile_064`
- Information Disclosure (1 case): `mobile_059`
- Insecure Data Storage (1 case): `mobile_033`

**Implementation Strategy**: Add Flutter/Dart patterns
- Cleartext: HTTP instead of HTTPS in networking code
- Secrets: Hardcoded keys in Dart constants
- Information Disclosure: print() statements with sensitive data
- Data Storage: Unencrypted local storage

---

## Phase 4: Infrastructure-as-Code Languages

### Priority 4A: YAML Support (CI/CD, K8s, Cloud)

**Categories**:
- CI/CD Security (3 cases): GitHub Actions, GitLab CI, Jenkins
- Container Security (2 cases): Kubernetes, Helm
- Cloud Database Security (3 cases): CloudFormation, Azure, GCP
- Datastore Security (3 cases): Various datastores
- Cloud Secrets Management (2 cases): CloudFormation, Azure

**Implementation Strategy**: Add YAML pattern detection
- CI/CD: Hardcoded secrets, missing permissions
- K8s: Privileged containers, missing resource limits
- Cloud: Public bucket access, weak IAM policies

---

### Priority 4B: Dockerfile Support (2 cases)

**Categories**:
- Container Security (2 cases): `docker_003`, `docker_013`

**Implementation Strategy**: Dockerfile security patterns
- Running as root: `USER root`
- Missing health checks
- Using `latest` tags
- Copying secrets into images

---

### Priority 4C: Terraform/HCL Support (2 cases)

**Categories**:
- Cloud IAM Misconfiguration (1 case): `terraform_002`
- Cloud Secrets Management (1 case): `terraform_006`

**Implementation Strategy**: Terraform/HCL patterns
- Overly permissive IAM policies
- Hardcoded secrets in `.tf` files
- Public S3 buckets, security groups

---

### Priority 4D: Groovy Support (1 case)

**Categories**:
- CI/CD Security (1 case): `jenkins_001`

**Implementation Strategy**: Jenkinsfile patterns
- Hardcoded credentials
- Unsafe shell execution
- Missing input validation

---

## Phase 5: Fill Language Gaps in Existing Detectors

### Priority 5A: TypeScript Gaps (2 cases)

**Categories**:
- Insecure JWT (2 cases): `typescript_007`, `typescript_008`
- SSRF (1 case): `typescript_010`

**Implementation**: TypeScript is already supported in most detectors, add to JWT and SSRF

---

### Priority 5B: PHP Gaps (6 cases)

**Categories**:
- Broken Access Control (1 case)
- CSRF (1 case)
- Insecure Deserialization (2 cases)
- Insecure Upload (1 case)
- SSRF (1 case)
- XXE (1 case)

**Implementation**: PHP partially supported, add missing patterns

---

### Priority 5C: Java, C#, Go, Rust, Ruby Gaps

**Java** (6 cases): broken_access_control, information_disclosure, insecure_upload, ldap_injection, open_redirect, race_condition, ssrf

**C#** (4 cases): broken_access_control, insecure_upload, ldap_injection, race_condition, ssrf

**Go** (3 cases): broken_access_control, insecure_upload, nosql_injection, ssrf

**Rust** (2 cases): broken_access_control, ssrf

**Ruby** (3 cases): broken_access_control, csrf, insecure_deserialization

---

## Implementation Timeline

### Week 1: High-Volume Languages
- ✅ Day 1-2: Scala support (10 detectors)
- ✅ Day 3-4: Elixir support (9 detectors)
- ✅ Day 5: Lua support (9 detectors)

### Week 2: Scripting & Mobile
- ✅ Day 6-7: Perl support (7 detectors)
- ✅ Day 8-9: Bash support (4 detectors)
- ✅ Day 10: Swift, Kotlin, Dart support (10 detectors combined)

### Week 3: Infrastructure-as-Code
- ✅ Day 11-12: YAML support (CI/CD, K8s, Cloud)
- ✅ Day 13: Dockerfile, Terraform, Groovy support

### Week 4: Language Gaps & Testing
- ✅ Day 14-15: Fill TypeScript, PHP, Java, C#, Go, Rust, Ruby gaps
- ✅ Day 16-17: Comprehensive testing of all 112 cases
- ✅ Day 18: Re-run benchmark and verify 0 UNSUPPORTED cases

---

## Success Metrics

**Target**: 0/760 UNSUPPORTED cases (0%)
**Current**: 112/760 UNSUPPORTED cases (14.7%)
**Improvement Needed**: -14.7% (eliminate all unsupported)

**Expected Impact on Vulnerability Detection**:
- Scala: +10 detections across 10 categories
- Elixir: +9 detections across 9 categories
- Lua: +9 detections across 9 categories
- Bash: +9 detections across 4 categories
- Other languages: +75 detections

**Total**: ~112 additional vulnerability detections

---

## Next Immediate Actions

1. **Start with Scala** - Highest category count (10), similar to Java patterns
2. **Then Elixir** - 9 categories, functional patterns similar to Erlang
3. **Then Bash** - High security impact (command injection, secrets in scripts)
4. **Parallel work on Infrastructure-as-Code** - YAML, Dockerfile patterns are distinct

---

**Generated**: 2026-03-31
**Priority**: CRITICAL - User requirement: "We should never have any Unsupported Language"
