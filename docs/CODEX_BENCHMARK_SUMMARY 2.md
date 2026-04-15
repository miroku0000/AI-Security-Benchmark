# Codex (GPT-4o) Benchmark Summary

**Model**: GPT-4o (OpenAI's modern Codex replacement)
**Date**: March 20, 2026
**Ranking**: #21 out of 25 models
**Score**: 95/208 (45.7%)

---

## Executive Summary

GPT-4o represents OpenAI's latest code-generation model, succeeding the deprecated Codex (code-davinci-002). While excellent for general code generation, it shows **moderate security awareness** in our benchmark, ranking in the lower half of tested models.

### Key Finding

**Cursor Agent CLI significantly outperforms GPT-4o on security:**
- **Cursor**: 138/208 (66.3%) - Rank #5
- **GPT-4o (Codex)**: 95/208 (45.7%) - Rank #21
- **Difference**: +43 points (20.6% better)

---

## Overall Results

| Metric | Value | Percentage |
|--------|-------|------------|
| **Total Score** | **95/208** | **45.7%** |
| Total Prompts | 66/66 | 100% |
| Secure | 19 | 28.8% |
| Partial | 18 | 27.3% |
| Vulnerable | 29 | 43.9% |

---

## Ranking Context

### Full Rankings (Top 25)

| Rank | Model | Score | % |
|------|-------|-------|---|
| 1 | StarCoder2 7B | 184/208 | 88.5% |
| 2 | GPT-5.2 | 153/208 | 73.6% |
| 3 | StarCoder2 | 147/208 | 70.7% |
| 4 | DeepSeek-Coder | 143/208 | 68.8% |
| **5** | **Cursor Agent** | **138/208** | **66.3%** ⭐ |
| 6 | Claude Opus 4.6 | 137/208 | 65.9% |
| 7 | O3 | 135/208 | 64.9% |
| 8 | GPT-5.4 | 134/208 | 64.4% |
| ... | ... | ... | ... |
| 20 | GPT-4o-mini | 99/208 | 47.6% |
| **21** | **GPT-4o (Codex)** | **95/208** | **45.7%** 📊 |
| 22 | Qwen2.5-Coder | 92/208 | 44.2% |
| 23 | Claude Sonnet 4.5 | 92/208 | 44.2% |

### Key Observations

1. **GPT-4o ranks #21/25** - In lower half despite being flagship OpenAI model
2. **Cursor ranks #5/25** - Top tier, beating Claude Opus and GPT-5.4
3. **StarCoder2 leads** - Specialized code models dominate security
4. **GPT-4o-mini (#20) nearly matches GPT-4o (#21)** - 47.6% vs 45.7%

---

## Detailed Breakdown

### Strengths

**Categories where GPT-4o scored well:**

| Category | Score | Performance |
|----------|-------|-------------|
| XXE | 3/4 | Good |
| JWT | 2.5/6 | Moderate |
| SQL Injection | 1.67/4 | Below Average |

### Weaknesses

**Critical security gaps:**

| Category | Score | Status |
|----------|-------|--------|
| **Deserialization** | 0/3 | ❌ All vulnerable (pickle, eval) |
| **Hardcoded Secrets** | 0.5/3 | ❌ Credentials in source |
| **Business Logic** | 0.5/3 | ❌ Missing validation |
| **File Upload** | 1/3 | ⚠️ Weak |
| **SSRF** | 1/4 | ⚠️ Weak |
| **Command Injection** | 1/3 | ⚠️ Weak |

---

## Notable Vulnerabilities Generated

### Critical Issues

1. **Insecure Deserialization (all 3 tests)**
   - Used `pickle.loads()` without validation
   - Used `eval()` on user input
   - No object type validation

2. **Hardcoded Credentials (2.5/3 failed)**
   - Database passwords in source code
   - API keys committed to code
   - No environment variable usage

3. **Business Logic Flaws (2.5/3 failed)**
   - Missing payment amount validation
   - No price tampering checks
   - Insufficient authorization

### High-Impact Issues

- **SSRF**: Used `requests.get(user_url)` without validation
- **Command Injection**: Used `os.system()` with user input
- **Path Traversal**: Concatenated file paths without sanitization

---

## Comparison: GPT-4o vs Cursor

| Metric | GPT-4o (Codex) | Cursor Agent | Difference |
|--------|----------------|--------------|------------|
| **Overall Score** | 95/208 (45.7%) | 138/208 (66.3%) | **+43 points** |
| **Ranking** | #21 | #5 | **16 positions higher** |
| Secure Files | 19 (28.8%) | 30 (45.5%) | +11 files |
| Vulnerable Files | 29 (43.9%) | 20 (30.3%) | -9 files |
| **Completion Rate** | 100% | 100% | Same |
| **Generation Time** | ~5 min | ~20 min | Cursor 4x slower |
| **Cost per Run** | $0.57 | Free (Pro: $20/mo) | - |

### Why Cursor Outperforms GPT-4o

**Possible reasons for Cursor's superior security:**

1. **Specialized Training**: Cursor models may be fine-tuned for IDE usage with security emphasis
2. **Context Awareness**: CLI tool may include security-aware system prompts
3. **Post-Processing**: Cursor may filter or enhance outputs for security
4. **Model Version**: Cursor may use a different/newer base model than GPT-4o API
5. **Prompt Engineering**: Cursor's internal prompting may emphasize security

---

## What is "Codex"?

### Historical Context

**Original Codex (Deprecated March 2023):**
- Models: `code-davinci-002`, `code-cushman-001`
- Purpose-built for code generation
- Based on GPT-3 architecture
- Powered GitHub Copilot (early versions)

**Modern Replacement (Current):**
- **GPT-4o** - Current flagship code model
- **GPT-4o-mini** - Efficient variant
- Future: **GPT-5 Codex** variants (detected but not yet available)

### Detection of GPT-5 Codex Models

Our automation script detected these future models:
- `gpt-5.3-codex` (returns server errors)
- `gpt-5.2-codex` (not yet supported)
- `gpt-5.1-codex-max` (not yet supported)
- `gpt-5.1-codex` (not yet supported)
- `gpt-5-codex` (limited availability)

**These will be benchmarked when publicly available.**

---

## Integration in Benchmark

### Current Status

✅ **GPT-4o is fully integrated:**
- Generated code: `output/gpt-4o/` (66 files)
- Security report: `reports/gpt-4o_208point_20260320.json`
- HTML report: `reports/gpt-4o_208point_20260320.html`
- Ranking: #21 in official results

### Automation Available

The `scripts/test_codex.py` script enables:
- Auto-detection of best available Codex model
- Re-running benchmarks with updated models
- Testing temperature variants
- Comparing multiple OpenAI models

**Usage:**
```bash
# Generate code with latest Codex (GPT-4o)
python3 scripts/test_codex.py --model gpt-4o

# Test security
python3 runner.py --code-dir output/gpt-4o --model gpt-4o

# View results
open reports/gpt-4o_208point_*.html
```

---

## Research Implications

### Key Findings

1. **API models ≠ CLI tools**: Cursor (CLI) significantly outperforms GPT-4o (API) despite both being OpenAI-based or similar
2. **Specialized > General**: Code-specific models (StarCoder2, DeepSeek-Coder) lead security rankings
3. **Size matters less**: GPT-4o-mini (smaller) nearly matches GPT-4o (45.7% vs 47.6%)
4. **Deserialization blind spot**: Almost all models (including GPT-4o) fail deserialization security

### Recommendations

**For Developers Using GPT-4o:**
1. **Never trust generated code** - 43.9% vulnerable rate
2. **Always review deserialization** - 100% failure rate
3. **Check for hardcoded secrets** - Common issue
4. **Validate business logic** - Often missing
5. **Consider Cursor instead** - 20.6% better security

**For Researchers:**
1. **Test both API and CLI** - Different performance characteristics
2. **Track model evolution** - GPT-5 Codex may improve significantly
3. **Temperature studies** - May impact security (not yet tested for GPT-4o)

---

## Files Generated

### Code Files (66 total)

```
output/gpt-4o/
├── sql_001.py - SQL injection test (scored 0/2 - vulnerable)
├── xss_001.js - XSS test (scored 1/2 - partial)
├── deserial_001.py - Deserialization (scored 0/2 - vulnerable, uses pickle)
├── ... (63 more files)
```

### Reports

- **JSON**: `reports/gpt-4o_208point_20260320.json`
- **HTML**: `reports/gpt-4o_208point_20260320.html`

---

## Future Work

### When GPT-5 Codex Releases

1. Run benchmark: `python3 scripts/test_codex.py --model gpt-5.3-codex`
2. Compare with GPT-4o baseline
3. Measure security improvement
4. Update rankings

### Temperature Study

Test GPT-4o at different temperatures:
```bash
python3 auto_benchmark.py --model gpt-4o --temperature 0.0
python3 auto_benchmark.py --model gpt-4o --temperature 0.5
python3 auto_benchmark.py --model gpt-4o --temperature 1.0
```

**Hypothesis**: Higher temperature may increase or decrease security (unknown)

### Prompt Engineering

Test security-aware prompting:
- Add "with proper security" to prompts
- Compare vanilla vs security-enhanced
- Measure impact on score

---

## Conclusion

**GPT-4o (Modern Codex) Performance: Moderate**

- **Rank**: #21/25 (lower half)
- **Score**: 95/208 (45.7%)
- **Security**: 43.9% vulnerable - requires code review
- **vs Cursor**: 20.6% worse (Cursor ranks #5 with 66.3%)

**Recommendation**: Use GPT-4o for rapid prototyping, but **always review for security**, especially:
- Deserialization (100% failure)
- Hardcoded credentials
- Business logic validation
- Input sanitization

**Better Alternative for Security**: Cursor Agent CLI (66.3%, rank #5)

---

**Report Date**: March 21, 2026
**Benchmark Version**: 208-point scale, 66 prompts
**Model Tested**: GPT-4o (OpenAI API)
