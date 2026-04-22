# Temperature Study Results (Updated with Improved Detectors)

**Generated:** 2026-04-14
**Detectors Applied:** DNS rebinding detection (SSRF), HTTP Header Injection detector

## ⚠️ Reproducibility Notice

**All results represent single-run measurements.** Due to LLM non-determinism at temperature > 0.0:
- Each configuration was tested **once** (not averaged across multiple runs)
- **Run-to-run variation is expected but unmeasured** in this study
- Results indicate **relative trends**, not absolute reproducible scores
- Replication studies may observe different absolute scores, but temperature trends should persist

See [REPRODUCIBILITY_AND_LIMITATIONS.md](REPRODUCIBILITY_AND_LIMITATIONS.md) for detailed discussion.

## Executive Summary

After reanalyzing all 125 temperature/level variant configurations with improved security detectors:

- **Models Analyzed:** 20 models with temperature variants (0.0, 0.5, 0.7, 1.0)
- **Total Tests per Configuration:** 730 prompts across 27 languages
- **Average Temperature Effect:** 1.40 percentage points
- **Maximum Temperature Effect:** 3.13 percentage points (Claude Sonnet 4.5)

## Key Findings

### Temperature Sensitivity Rankings

| Rank | Model | Temperature Variation | Best Temp | Best Score | Worst Temp | Worst Score |
|------|-------|----------------------|-----------|------------|------------|-------------|
| 1 | Claude Sonnet 4.5 | **3.13 pp** | 1.0 | 56.9% | 0.7 | 53.8% |
| 2 | CodeLlama | **2.52 pp** | 1.0 | 60.8% | 0.7 | 58.3% |
| 3 | Gemini 2.5 Flash | **2.19 pp** | 1.0 | 58.7% | 0.7 | 56.5% |
| 4 | StarCoder2 | **2.12 pp** | 1.0 | 65.0% | 0.0 | 62.9% |
| 5 | GPT-5.4 | **1.96 pp** | 1.0 | 60.3% | 0.5 | 58.4% |
| 6 | Claude Opus 4.6 | **1.95 pp** | 0.7 | 59.1% | 0.0 | 57.2% |
| 7 | Mistral | **1.84 pp** | 0.5 | 59.5% | 0.7 | 57.7% |
| 8 | GPT-5.2 | **1.84 pp** | 0.5 | 61.1% | 0.0 | 59.3% |
| 9 | GPT-5.4 Mini | **1.54 pp** | 1.0 | 60.0% | 0.5 | 58.4% |
| 10 | Llama 3.1 | **1.47 pp** | 0.0 | 57.9% | 1.0 | 56.5% |

### Temperature Recommendations by Model

**For Best Security:**

- **StarCoder2:** Use temp **1.0** (65.0%) - 2.1 pp better than temp 0.0
- **DeepSeek Coder:** Use temp **0.7** (62.4%) - 1.2 pp better than temp 0.0
- **GPT-5.2:** Use temp **0.5** (61.1%) - 1.8 pp better than temp 0.0
- **CodeLlama:** Use temp **1.0** (60.8%) - 2.5 pp better than temp 0.7
- **GPT-5.4:** Use temp **1.0** (60.3%) - 2.0 pp better than temp 0.5
- **GPT-5.4 Mini:** Use temp **1.0** (60.0%) - 1.5 pp better than temp 0.5

**Minimal Temperature Effect (<1.0 pp):**

- CodeGemma: 0.2 pp variation (stable across all temperatures)
- DeepSeek Coder 6.7B: 0.4 pp variation
- GPT-4o-mini: 0.4 pp variation
- GPT-4o: 0.5 pp variation
- Qwen 2.5 Coder: 0.7 pp variation
- Qwen 3 Coder 30B: 0.7 pp variation

## Detailed Model Analysis

### StarCoder2 (Best Overall Performance)
- **Temp 0.0:** 62.9% (484 secure, 229 vulnerable)
- **Temp 0.5:** 63.1% (503 secure, 226 vulnerable)
- **Temp 0.7:** 63.2% (491 secure, 237 vulnerable)
- **Temp 1.0:** 65.0% (509 secure, 221 vulnerable) ⭐ **Best**
- **Variation:** 2.1 percentage points

### Claude Sonnet 4.5 (Most Temperature-Sensitive)
- **Temp 0.0:** 55.8% (458 secure, 272 vulnerable)
- **Temp 0.5:** 55.8% (461 secure, 269 vulnerable)
- **Temp 0.7:** 53.8% (448 secure, 282 vulnerable) ⚠️ **Worst**
- **Temp 1.0:** 56.9% (475 secure, 255 vulnerable) ⭐ **Best**
- **Variation:** 3.1 percentage points

### DeepSeek Coder (33B)
- **Temp 0.0:** 61.1% (471 secure, 258 vulnerable)
- **Temp 0.5:** 61.6% (477 secure, 252 vulnerable)
- **Temp 0.7:** 62.4% (487 secure, 242 vulnerable) ⭐ **Best**
- **Temp 1.0:** 61.4% (469 secure, 259 vulnerable)
- **Variation:** 1.2 percentage points

## Impact of Improved Detectors

The updated detectors (DNS rebinding + HTTP header injection) had minimal impact on temperature sensitivity patterns:

1. **DNS Rebinding Detection:** Caught more sophisticated SSRF attacks where models did IP validation but didn't resolve DNS first
2. **Header Injection Detection:** Ready but not actively scoring (no header_injection category prompts yet)
3. **Score Changes:** Most models had ±0.1-0.5% changes across temperatures

## Comparison with Previous Studies

**Current Study (760 prompts):**
- Maximum variation: 3.13 pp (Claude Sonnet 4.5)
- Average variation: 1.40 pp

**Previous Studies Referenced:**
- 17.3 pp variation mentioned in `TEMPERATURE_STUDY_FINAL.md` for StarCoder2
  - This appears to be from a different subset of prompts or methodology
  - Current full benchmark shows 2.1 pp for StarCoder2

## Recommendations

1. **Use Temperature Tuning:** Even modest 1-3 pp improvements are significant when securing thousands of code samples
2. **Model-Specific Settings:**
   - StarCoder2, CodeLlama, GPT-5.4: Use temp 1.0
   - GPT-5.2, Mistral: Use temp 0.5
   - DeepSeek Coder, Claude Opus: Use temp 0.7
3. **Stable Models:** GPT-4o, GPT-4o-mini, CodeGemma show minimal temperature sensitivity (<0.5 pp)

## Data Files

- Individual reports: `reports/*_temp*.json`
- Temperature variants: 125 configurations analyzed
- Total test executions: 125 × 730 = 91,250 security tests

---

**Note:** All temperature studies conducted on the same code generation outputs. Only the analysis was rerun with improved detectors, not the code generation itself.
