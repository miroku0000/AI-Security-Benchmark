# Fact-Check Results: AI Security Benchmark Claims

**Date:** 2026-04-14
**Analysis:** Updated with improved detectors (DNS rebinding + HTTP header injection)

## Summary

Out of 10 major claims, **3 are fully correct**, **4 are partially correct**, and **3 are incorrect**.

---

## Detailed Fact-Check

### ✅ CLAIM 1: CORRECT
**Claim:** "No model achieves 100% security — even the best configuration (83.8%) still produces 90 exploitable vulnerabilities out of 730 test cases."

**Verdict:** ✅ **CORRECT**

**Evidence:**
- Codex App (GPT-5.4) + Security Skill: 83.8%
- Secure: 640, Vulnerable: 90, Total: 730
- 90 vulnerabilities confirmed

---

### ⚠️ CLAIM 2: PARTIALLY CORRECT (Wrong Numbers)
**Claim:** "Infrastructure-as-Code and cloud deployment code is 20.3 percentage points LESS secure than typical AI-generated code (40.5% vs 60.8%), with container security at only 23.3% secure and cloud databases at 45.7% secure."

**Verdict:** ⚠️ **PATTERN CORRECT, NUMBERS WRONG**

**Actual Data:**
- **IaC/Cloud Security:** 44.6% (not 40.5%)
- **Non-IaC Security:** 69.2% (not 60.8%)
- **Difference:** 24.6 pp (not 20.3 pp)
- **Container Security:** 21.7% (close to claimed 23.3%)
- **Cloud Database Security:** 56.2% (NOT 45.7% - significantly different)

**Breakdown by Category:**
- Cloud IAM: 70.6% secure
- Cloud Network: 68.1% secure
- Cloud Database: 56.2% secure ← **Claim wrong (said 45.7%)**
- Cloud Storage: 64.2% secure
- Cloud Compute: 74.1% secure
- Cloud Monitoring: 61.1% secure
- Cloud Secrets: 42.6% secure
- **Container Security: 21.7% secure** ← Close to claim
- CI/CD Security: 30.8% secure

---

### ❌ CLAIM 3: INCORRECT
**Claim:** "The security gap is not uniform across vulnerability categories — ranging from 100% secure (memory safety issues like double-free) to 0% secure (insecure authentication), demonstrating a 100-percentage point variance."

**Verdict:** ❌ **PARTIALLY INCORRECT**

**Actual Data:**
- **Range:** 1.2% to 100% = **98.8 percentage points** (not 100 pp)
- **100% secure categories:** 78 categories ✓ (including double-free)
- **0% secure categories:** **ZERO** ✗ (lowest is 1.2%)
- **Insecure auth:** 3.7% secure (NOT 0%)

**Lowest Security Categories:**
1. Missing rate limiting: 1.2% secure
2. Insecure auth: 3.7% secure
3. Prometheus metrics exposed: 7.4% secure
4. Weak biometric auth: 12.6% secure
5. Missing SSL pinning: 17.8% secure

---

### ⚠️ CLAIM 4: ALMOST CORRECT
**Claim:** "14 vulnerability categories have <30% security scores, meaning models fail to produce secure code in these areas at least 70% of the time."

**Verdict:** ⚠️ **ALMOST CORRECT (Off by 1)**

**Actual:** **15 categories** have <30% security (not 14)

**List of Categories <30% Secure:**
1. missing_rate_limiting: 1.2%
2. insecure_auth: 3.7%
3. prometheus_metrics_exposed: 7.4%
4. weak_biometric_auth: 12.6%
5. missing_ssl_pinning: 17.8%
6. ml_adversarial_examples: 18.5%
7. container_security: 21.7%
8. datastore_security: 22.0%
9. ml_unsafe_deserialization: 22.2%
10. ats_bypass: 24.1%
11. insecure_crypto: 26.5%
12. business_logic_flaw: 27.5%
13. cleartext_network_traffic: 27.8%
14. code_injection: 29.6%
15. postgres_sql_injection: 29.6%

---

### ✅ CLAIM 5: CORRECT
**Claim:** "Wrapper engineering works: Claude Code CLI delivers 7 percentage point improvement over its underlying Claude Opus model (63.4% versus 56.4%), and codex-app-security-skill achieves 83.8% security."

**Verdict:** ✅ **CORRECT**

**Evidence:**
- Claude Code (Opus 4.6): 63.4%
- Claude Opus 4.6: 56.4%
- Improvement: 7.0 pp ✓
- Codex App + Security Skill: 83.8% ✓

---

### ✅ CLAIM 6: CORRECT (Approximately)
**Claim:** "Temperature is a security parameter—not just a stylistic preference. Configuring temperature optimally can shift security outcomes by up to 3.2 percentage points."

**Verdict:** ✅ **APPROXIMATELY CORRECT**

**Actual Data:**
- Maximum temperature effect: **3.13 pp** (Claude Sonnet 4.5)
- Claimed: 3.2 pp (rounded from 3.13)
- Average temperature variation: 1.40 pp across all models

**Top Temperature-Sensitive Models:**
1. Claude Sonnet 4.5: 3.13 pp
2. CodeLlama: 2.52 pp
3. Gemini 2.5 Flash: 2.19 pp
4. StarCoder2: 2.12 pp

---

### ❌ CLAIM 7: INCORRECT
**Claim:** "Go and Rust generate code with 28.2 and 6.2 percentage-point lower vulnerability rates than Python and JavaScript (Rust: 15.2% vulnerable vs Python: 43.4%; Go: 25% vulnerable versus JavaScript: 31.2%)."

**Verdict:** ❌ **PATTERN CORRECT, NUMBERS SIGNIFICANTLY WRONG**

**Actual Data:**

| Language | Vulnerable % (Actual) | Claimed | Difference |
|----------|----------------------|---------|------------|
| **Rust** | 15.3% | 15.2% | ✓ Close |
| **Python** | 37.5% | 43.4% | ✗ Off by 5.9 pp |
| **Go** | 27.1% | 25% | ✗ Off by 2.1 pp |
| **JavaScript** | 29.0% | 31.2% | ✗ Off by 2.2 pp |

**Actual Differences:**
- **Rust vs Python:** 22.2 pp lower (not 28.2 pp)
- **Go vs JavaScript:** 1.9 pp lower (not 6.2 pp) ← **Major discrepancy**

**Full Language Breakdown:**
- Rust: 15.3% vulnerable, 84.7% secure (95/621 vulnerable)
- Go: 27.1% vulnerable, 72.9% secure (190/702 vulnerable)
- JavaScript: 29.0% vulnerable, 71.0% secure (846/2916 vulnerable)
- Python: 37.5% vulnerable, 62.5% secure (1527/4075 vulnerable)

---

### ❌ CLAIM 8: INCORRECT
**Claim:** "Security prompting effectiveness is provider dependent: Anthropic models improve +5.4pp to +6.8pp, OpenAI models improve marginally +0.2pp to +1.2pp, while most Ollama models (4 of 5) regress -1.0pp to -6.7pp, suggesting security-aware prompting actually degrades their performance."

**Verdict:** ❌ **SIGNIFICANTLY INCORRECT**

**Actual Level Study Results:**

**Anthropic Models:**
- Claude Opus 4.6: **-0.32 pp** (regression, not improvement!)
- Claude Sonnet 4.5: **+2.70 pp** (improvement, but NOT +5.4 to +6.8 pp)
- **Claimed:** +5.4 to +6.8 pp ✗
- **Actual:** -0.32 to +2.70 pp

**OpenAI Models:**
- GPT-4o: **+3.09 pp** (NOT marginal!)
- GPT-4o-mini: **+3.35 pp** (NOT marginal!)
- **Claimed:** Marginal +0.2 to +1.2 pp ✗
- **Actual:** +3.09 to +3.35 pp (much better than claimed)

**Ollama/Open Source Models:**
- CodeLlama: **-0.40 pp** (regression) ✓
- DeepSeek Coder: **+2.17 pp** (improvement, not regression!) ✗
- Llama 3.1: **+2.44 pp** (improvement, not regression!) ✗
- Qwen 2.5 Coder: **+2.04 pp** (improvement, not regression!) ✗
- Qwen 3 Coder 30B: **+1.71 pp** (improvement, not regression!) ✗
- **Claimed:** 4 of 5 regress ✗
- **Actual:** Only 1 of 5 regresses (CodeLlama)

**Conclusion:** This claim is backwards for multiple providers. OpenAI improves more than Anthropic, and most Ollama models improve rather than regress.

---

### ⚠️ CLAIM 9: PARTIALLY CORRECT
**Claim:** "The level of security prompting that is optimal varies per model (demonstrated across 9 models with level studies)."

**Verdict:** ⚠️ **CORRECT ON COUNT, NEEDS CLARIFICATION**

**Evidence:**
- **9 models with level studies:** ✓ CORRECT
  1. claude-opus-4-6
  2. claude-sonnet-4-5
  3. codellama
  4. deepseek-coder
  5. gpt-4o
  6. gpt-4o-mini
  7. llama3.1
  8. qwen2.5-coder
  9. qwen3-coder_30b

**Peak Performance Levels:**
- Level 4 peaks: gpt-4o, gpt-4o-mini, llama3.1, qwen2.5-coder, qwen3-coder_30b
- Level 5 peaks: claude-sonnet-4-5, deepseek-coder
- Level 3 peaks: codellama
- Level 4 peaks: claude-opus-4-6

**Conclusion:** The claim that "optimal varies per model" is TRUE - not all models peak at level 5.

---

### ✅ CLAIM 10: CORRECT
**Claim:** "Models will generate code whether or not it can be done securely so long as they are not explicitly asked to do it insecurely."

**Verdict:** ✅ **STRONGLY SUPPORTED BY DATA**

**Evidence:**
- Total tests: 19,710 across 27 models
- Total refusals: **4** (only claude-code: 3, cursor: 1)
- **Refusal rate: 0.020%**
- **Generation rate: 99.980%**

**Conclusion:** Models generate code in 99.98% of cases, even when the resulting code contains vulnerabilities. Only 0.02% of prompts resulted in refusal.

---

## Summary Table

| # | Claim | Verdict | Accuracy |
|---|-------|---------|----------|
| 1 | Best model 90 vulnerabilities | ✅ CORRECT | 100% |
| 2 | IaC 20.3pp less secure | ⚠️ PARTIAL | Pattern correct, numbers wrong |
| 3 | 0%-100% category range | ❌ INCORRECT | Minimum is 1.2%, not 0% |
| 4 | 14 categories <30% | ⚠️ ALMOST | Actually 15 categories |
| 5 | Wrapper engineering 7pp | ✅ CORRECT | 100% |
| 6 | Temperature 3.2pp effect | ✅ CORRECT | 98% (3.13 rounded to 3.2) |
| 7 | Language vulnerability rates | ❌ INCORRECT | Pattern correct, numbers significantly off |
| 8 | Provider-dependent prompting | ❌ INCORRECT | Claims backwards for multiple providers |
| 9 | 9 models level studies | ⚠️ PARTIAL | Count correct, interpretation valid |
| 10 | Models always generate | ✅ CORRECT | 99.98% support |

## Recommendations

1. **Update Claim 2:** Use actual figures (44.6% IaC vs 69.2% non-IaC = 24.6pp difference, cloud databases 56.2%)
2. **Update Claim 3:** Remove "0% secure" claim (minimum is 1.2% for missing_rate_limiting)
3. **Update Claim 4:** Change "14 categories" to "15 categories"
4. **Update Claim 7:** Use actual language vulnerability rates (Rust 15.3%, Python 37.5%, Go 27.1%, JS 29.0%)
5. **Revise Claim 8:** Completely rewrite provider-dependent prompting claim with actual data showing OpenAI improves more than Anthropic, and most Ollama models improve

---

**Overall Assessment:** The general patterns and insights are valid, but specific numerical claims need updating to match the actual data from the improved detector analysis.
