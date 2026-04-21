# Complete Security Score Variation Analysis - All 20 Models

**Analysis Date:** 2026-04-20 10:33:46
**Duration:** 0:28:07.202735
**Models Analyzed:** 20
**Prompts per Model:** 50 (sampled)
**Total Security Tests:** 1000 (50 prompts × 5 runs × 20 models)

---

## Executive Summary

- **Average score variation range:** 23.00 percentage points
- **Median score variation range:** 0.00 pp
- **Average standard deviation:** 11.04 pp
- **Maximum variation observed:** 100.00 pp

### Variation Distribution

- **Minimal variation (≤1pp):** 67.8%
- **Moderate variation (1-5pp):** 0.0%
- **Significant variation (>5pp):** 32.2%
- **Extreme variation (≥90pp):** 13.8%

---

## Interpretation

**High variation** - Significant score differences across runs

## Comparison: Code vs Score Variation

- **Code variation:** 72.4% of code files differ across runs
- **Score variation (>1pp):** 32.2%
- **Significant score variation (>5pp):** 32.2%
- **Insight:** Different code often produces similar security scores

---

## Model Consistency Rankings

Models ranked by consistency (% of tests with ≤1pp variation):

| Rank | Model | Consistency | Avg Range | Max Range |
|------|-------|-------------|-----------|-----------|
| 1 | qwen3-coder_30b | 82.0% | 10.00pp | 100.00pp |
| 2 | claude-sonnet-4-5 | 80.0% | 12.00pp | 100.00pp |
| 3 | gpt-4 | 80.0% | 16.00pp | 100.00pp |
| 4 | qwen2.5-coder_14b | 80.0% | 13.00pp | 100.00pp |
| 5 | gpt-3.5-turbo | 78.0% | 14.00pp | 100.00pp |
| 6 | gpt-4o-mini | 76.0% | 18.00pp | 100.00pp |
| 7 | codegemma | 72.0% | 20.00pp | 100.00pp |
| 8 | gpt-5.4-mini | 72.0% | 20.00pp | 100.00pp |
| 9 | gpt-5.4 | 70.0% | 21.00pp | 100.00pp |
| 10 | mistral | 70.0% | 20.00pp | 100.00pp |
| 11 | claude-opus-4-6 | 66.0% | 22.00pp | 100.00pp |
| 12 | codellama | 64.0% | 26.00pp | 100.00pp |
| 13 | gpt-4o | 64.0% | 25.00pp | 100.00pp |
| 14 | gpt-5.2 | 64.0% | 24.00pp | 100.00pp |
| 15 | llama3.1 | 64.0% | 23.00pp | 100.00pp |
| 16 | deepseek-coder_6.7b-instruct | 62.0% | 29.00pp | 100.00pp |
| 17 | gemini-2.5-flash | 62.0% | 28.00pp | 100.00pp |
| 18 | qwen2.5-coder | 62.0% | 27.00pp | 100.00pp |
| 19 | starcoder2 | 46.0% | 43.00pp | 100.00pp |
| 20 | deepseek-coder | 42.0% | 49.00pp | 100.00pp |

---

## Key Findings

1. **Overall consistency:** 67.8% of scores vary by ≤1pp
2. **Significant variation:** 32.2% vary by >5pp
3. **Extreme cases:** 13.8% show ≥90pp variation (0-100%)
4. **Model differences:** Consistency rates range across model families
5. **Temperature 1.0 impact:** Measurable but manageable non-determinism

---

## Implications

- **For 68% of prompts:** Security behavior is consistent and reliable
- **For 32% of prompts:** Multiple runs recommended for critical applications
- **Enterprise guidance:** Use temperature 0.0 for consistency or validate all outputs
- **Benchmark validity:** Relative model rankings remain meaningful despite variation

---

## All Models Analyzed

1. claude-opus-4-6
2. claude-sonnet-4-5
3. codegemma
4. codellama
5. deepseek-coder_6.7b-instruct
6. deepseek-coder
7. gemini-2.5-flash
8. gpt-3.5-turbo
9. gpt-4
10. gpt-4o-mini
11. gpt-4o
12. gpt-5.2
13. gpt-5.4-mini
14. gpt-5.4
15. llama3.1
16. mistral
17. qwen2.5-coder_14b
18. qwen2.5-coder
19. qwen3-coder_30b
20. starcoder2

---

**Full Data:** `all_models_security_score_variation_20260420_103346.json`
