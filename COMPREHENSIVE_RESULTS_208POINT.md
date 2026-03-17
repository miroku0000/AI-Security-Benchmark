# Comprehensive AI Security Benchmark Results - 208 Point Scale

**Generated:** 2026-02-08 20:55:19  
**Total Models Tested:** 20  
**Benchmark Version:** 208-point scale (66 test cases, 25 detectors)

---

## Executive Summary

This benchmark evaluated 20 AI models on their ability to generate secure code across 66 different security scenarios covering SQL injection, XSS, path traversal, command injection, authentication flaws, and more.

### Top Performers

1. **starcoder2:7b** - 180/208 (86.5%) - 51 secure, 7 vulnerable
2. **starcoder2** - 146/208 (70.2%) - 40 secure, 12 vulnerable
3. **gpt-5.2** - 144/208 (69.2%) - 34 secure, 14 vulnerable
4. **deepseek-coder** - 136/208 (65.4%) - 32 secure, 16 vulnerable
5. **o3** - 117/208 (56.2%) - 23 secure, 23 vulnerable


---

## Complete Rankings

| Rank | Model | Score | % | Secure | Partial | Vulnerable |
|------|-------|-------|---|--------|---------|------------|
| 1 | starcoder2:7b | 180/208 | 86.5% | 51 | 7 | 7 |
| 2 | starcoder2 | 146/208 | 70.2% | 40 | 13 | 12 |
| 3 | gpt-5.2 | 144/208 | 69.2% | 34 | 18 | 14 |
| 4 | deepseek-coder | 136/208 | 65.4% | 32 | 18 | 16 |
| 5 | o3 | 117/208 | 56.2% | 23 | 20 | 23 |
| 6 | codellama | 115/208 | 55.3% | 19 | 18 | 29 |
| 7 | codegemma:7b-instruct | 113/208 | 54.3% | 25 | 15 | 26 |
| 8 | deepseek-coder:6.7b-instruct | 108/208 | 51.9% | 20 | 20 | 26 |
| 9 | gpt-4 | 105/208 | 50.5% | 21 | 19 | 26 |
| 10 | o3-mini | 104/208 | 50.0% | 18 | 19 | 29 |
| 11 | mistral | 104/208 | 50.0% | 16 | 20 | 30 |
| 12 | llama3.1 | 100/208 | 48.1% | 14 | 25 | 27 |
| 13 | o1 | 100/208 | 48.1% | 16 | 20 | 30 |
| 14 | codegemma | 100/208 | 48.1% | 19 | 17 | 30 |
| 15 | gpt-4o | 93/208 | 44.7% | 17 | 16 | 33 |
| 16 | claude-sonnet-4-5-old | 92/208 | 44.2% | 16 | 21 | 29 |
| 17 | gpt-4o-mini | 90/208 | 43.3% | 15 | 19 | 32 |
| 18 | qwen2.5-coder:14b | 90/208 | 43.3% | 15 | 20 | 31 |
| 19 | gpt-3.5-turbo | 87/208 | 41.8% | 17 | 14 | 35 |
| 20 | qwen2.5-coder | 86/208 | 41.4% | 12 | 18 | 36 |


---

## Key Findings

### Winner: starcoder2:7b

**Score:** 180/208 (86.5%)  
**Security Profile:**
- ✅ Secure: 51/66 test cases (77.3%)
- ⚠️  Partial: 7/66 test cases (10.6%)
- ❌ Vulnerable: 7/66 test cases (10.6%)

### Comparison to Previous Best (Claude Opus 4.6: 137/208)

The winning model **starcoder2:7b** scored **180 points** compared to Claude Opus 4.6's 137 points:
- **Improvement:** +43 points (31.4% better)
- **Percentage:** 86.5% vs 65.9%

### Performance Tiers

#### Tier 1: Excellent (>70%)
- starcoder2:7b: 180/208 (86.5%)
- starcoder2: 146/208 (70.2%)


#### Tier 2: Good (60-70%)
- gpt-5.2: 144/208 (69.2%)
- deepseek-coder: 136/208 (65.4%)


#### Tier 3: Average (50-60%)
- o3: 117/208 (56.2%)
- codellama: 115/208 (55.3%)
- codegemma:7b-instruct: 113/208 (54.3%)
- deepseek-coder:6.7b-instruct: 108/208 (51.9%)
- gpt-4: 105/208 (50.5%)
- o3-mini: 104/208 (50.0%)
- mistral: 104/208 (50.0%)


#### Tier 4: Below Average (<50%)
- llama3.1: 100/208 (48.1%)
- o1: 100/208 (48.1%)
- codegemma: 100/208 (48.1%)
- gpt-4o: 93/208 (44.7%)
- claude-sonnet-4-5-old: 92/208 (44.2%)
- gpt-4o-mini: 90/208 (43.3%)
- qwen2.5-coder:14b: 90/208 (43.3%)
- gpt-3.5-turbo: 87/208 (41.8%)
- qwen2.5-coder: 86/208 (41.4%)


---

## Analysis by Model Family

### OpenAI Models
- gpt-5.2: 144/208 (69.2%)
- o3: 117/208 (56.2%)
- gpt-4: 105/208 (50.5%)
- o3-mini: 104/208 (50.0%)
- o1: 100/208 (48.1%)
- gpt-4o: 93/208 (44.7%)
- gpt-4o-mini: 90/208 (43.3%)
- gpt-3.5-turbo: 87/208 (41.8%)


### Anthropic Models
- claude-sonnet-4-5-old: 92/208 (44.2%)


### Open-Source Code Models (Ollama)
- starcoder2:7b: 180/208 (86.5%)
- starcoder2: 146/208 (70.2%)
- deepseek-coder: 136/208 (65.4%)
- codellama: 115/208 (55.3%)
- codegemma:7b-instruct: 113/208 (54.3%)
- deepseek-coder:6.7b-instruct: 108/208 (51.9%)
- mistral: 104/208 (50.0%)
- llama3.1: 100/208 (48.1%)
- codegemma: 100/208 (48.1%)
- qwen2.5-coder:14b: 90/208 (43.3%)
- qwen2.5-coder: 86/208 (41.4%)


---

## Methodology

- **Test Cases:** 66 prompts covering 15+ vulnerability categories
- **Detectors:** 25 security detectors analyzing generated code
- **Scoring:** Maximum 208 points (weighted by vulnerability severity)
- **Categories:** SQL injection, XSS, path traversal, command injection, auth, crypto, and more

---

## Conclusion

**starcoder2:7b** is the clear winner with **180/208 (86.5%)**, significantly outperforming all other tested models including Claude Opus 4.6 (65.9%).

The benchmark reveals significant variation in security awareness across AI models, with scores ranging from 41.4% to 86.5%.

---

*Report generated automatically by AI Security Benchmark v2.0*
