# Testing Codex.app with Security Best Practice Skill

## Overview

This document describes how to test OpenAI's Codex.app with the Security Best Practice Skill enabled and compare results against the baseline (no skill).

## Prerequisites

1. **Codex.app installed** - Available from OpenAI
2. **Security Best Practice Skill installed in Codex.app**
   - Open Codex.app
   - Navigate to Settings → Skills
   - Install "Security Best Practice" skill
   - Ensure it's enabled

3. **AI Security Benchmark repository**
   ```bash
   git clone <repository-url>
   cd AI_Security_Benchmark
   ```

## Testing Process

### Step 1: Baseline Test (No Security Skill)

Generate code without the security skill to establish a baseline:

```bash
# Generate all 140 prompts
python3 -u scripts/test_codex_app.py \
  --output-dir output/codex-app-baseline \
  --timeout 120

# Run security analysis
python3 runner.py \
  --code-dir output/codex-app-baseline \
  --model codex-app-baseline
```

**Expected Output:**
- 110 code files generated (Python, JavaScript, Java, Go, Rust)
- Security report: `reports/codex-app-baseline_208point_YYYYMMDD.json`
- HTML report: `reports/benchmark_report.html`

### Step 2: Security Skill Test

**IMPORTANT**: Enable the Security Best Practice Skill in Codex.app before running this test.

Generate code with the security skill enabled:

```bash
# Generate all 140 prompts with security skill
python3 -u scripts/test_codex_app.py \
  --output-dir output/codex-app-security-skill \
  --timeout 120

# Run security analysis
python3 runner.py \
  --code-dir output/codex-app-security-skill \
  --model codex-app-security-skill
```

**Expected Output:**
- 110 code files generated (same languages as baseline)
- Security report: `reports/codex-app-security-skill_208point_YYYYMMDD.json`
- HTML report with security comparison

### Step 3: Compare Results

The security reports will show:
- **Overall Security Score** (out of 290 points)
- **Secure Code Percentage** (files with no vulnerabilities)
- **Vulnerability Breakdown** by category
- **Specific Vulnerabilities** detected in each file

## Understanding the Results

### Baseline Metrics (Example from Testing)
```
Model: codex-app-baseline
Total Prompts:   140
Completed Tests: 110 (78.6%)
Failed Gen:      30 (21.4%)  [C# and C++ not supported by script]

Security Results:
Secure:          87 (79.1%)
Partial:         5 (4.5%)
Vulnerable:      18 (16.4%)
Overall Score:   249/290 (85.9%)
```

### Security Skill Metrics
To be compared after test completes. Key questions:
1. **Does the skill increase the security score?**
2. **Which vulnerability categories show improvement?**
3. **Are there any regressions?**

## Interpreting Scores

### Score Breakdown (208-point scale per file)
Each file is tested for multiple security issues:
- SQL Injection
- Cross-Site Scripting (XSS)
- Path Traversal
- Command Injection
- Insecure Authentication
- JWT Security
- Hardcoded Secrets
- And more...

### Vulnerability Severity
- **CRITICAL**: Hardcoded credentials, SQL injection
- **HIGH**: Command injection, XXE, business logic flaws
- **MEDIUM**: Missing security flags, weak crypto
- **LOW**: Minor security concerns
- **INFO**: Language not supported by analyzer

## Known Limitations

1. **C# and C++ Not Supported**
   - The `test_codex_app.py` script currently only supports:
     - Python (.py)
     - JavaScript (.js)
     - Java (.java)
     - Go (.go)
     - Rust (.rs)
   - 30 prompts require C#/C++ and will be skipped

2. **Skill Activation**
   - Ensure the Security Best Practice Skill is **active** in Codex.app
   - Skills must be enabled before running the benchmark
   - Check Codex.app → Settings → Skills to verify

3. **Timeout Considerations**
   - Default timeout: 120 seconds per prompt
   - Some prompts may timeout if skill adds processing time
   - Adjust with `--timeout` flag if needed

## Reproducing Tests

To reproduce the exact test environment:

```bash
# Install dependencies
pip install -r requirements.txt

# Verify Codex.app is accessible
python3 scripts/test_codex_app.py --check

# Run baseline test
python3 -u scripts/test_codex_app.py \
  --output-dir output/codex-app-baseline \
  --timeout 120 \
  > codex-baseline.log 2>&1

# Enable Security Skill in Codex.app UI

# Run security skill test
python3 -u scripts/test_codex_app.py \
  --output-dir output/codex-app-security-skill \
  --timeout 120 \
  > codex-security-skill.log 2>&1

# Run security analysis on both
python3 runner.py --code-dir output/codex-app-baseline --model codex-app-baseline
python3 runner.py --code-dir output/codex-app-security-skill --model codex-app-security-skill

# Compare reports
diff reports/codex-app-baseline_208point_*.json \
     reports/codex-app-security-skill_208point_*.json
```

## Expected Timeline

- **Code Generation**: ~5-10 minutes per run (140 prompts, 120s timeout)
  - With caching: ~1-2 minutes for subsequent runs
- **Security Analysis**: ~2-3 minutes per run
- **Total Time**: ~15-30 minutes for complete comparison

## Output Files

### Generated Code
```
output/codex-app-baseline/
├── sql_001.py
├── sql_002.js
├── xss_001.js
└── ... (110 files)

output/codex-app-security-skill/
├── sql_001.py
├── sql_002.js
├── xss_001.js
└── ... (110 files)
```

### Reports
```
reports/
├── codex-app-baseline_208point_YYYYMMDD.json
├── codex-app-baseline_208point_YYYYMMDD.html
├── codex-app-security-skill_208point_YYYYMMDD.json
└── codex-app-security-skill_208point_YYYYMMDD.html
```

### Logs
```
codex-baseline.log              # Generation log for baseline
codex-security-skill.log        # Generation log with skill
codex-baseline-test-run.log     # Security test log for baseline
codex-security-skill-test-run.log  # Security test log with skill
```

## Hypothesis

**Expected Improvement with Security Skill:**
- Higher overall security score (>85.9% baseline)
- Fewer vulnerable files (<18/110 baseline)
- Better handling of:
  - Hardcoded credentials
  - SQL injection prevention
  - Input validation
  - Secure cryptography

## Whitepaper Inclusion

This test methodology should be included in the whitepaper under:

**Section: "Impact of Security-Focused Prompting and Skills"**

Key findings to document:
1. Baseline security score without skill
2. Security score with skill enabled
3. Delta (improvement percentage)
4. Category-specific improvements
5. Any regressions or trade-offs
6. Comparison with other models (GPT-4o, Claude, etc.)

## Future Enhancements

1. Add C#/C++ support to test script
2. Test additional Codex.app skills
3. Measure performance impact of skill activation
4. Test skill combinations
5. Compare against dedicated security analysis tools

## References

- Codex.app Documentation: https://openai.com/codex
- Security Best Practice Skill: [Codex.app Skills Marketplace]
- Benchmark Repository: [This repository]

---

**Last Updated**: 2026-03-22
**Test Version**: v2.0
**Codex.app Version**: 0.116.0-alpha.10
