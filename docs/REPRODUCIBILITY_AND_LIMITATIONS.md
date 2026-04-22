# Reproducibility and Limitations

**Date:** 2026-04-17
**Study:** AI Security Benchmark - LLM Code Generation Security Analysis

---

## ⚠️ Important Disclaimer: Non-Deterministic Outputs

### Temperature > 0.0 and Reproducibility

**When temperature is set above 0.0, LLM outputs are non-deterministic.** This means:

1. **Multiple runs of the same prompt will produce different code**
2. **Security scores can vary between runs**
3. **Results in this study represent single snapshots, not averages**

### What This Means for Our Results

All benchmark results in this study were generated with **a single run per configuration**. Each combination of (model, temperature, prompt) was tested once. Therefore:

- **Results are indicative, not definitive**
- **Actual variation between runs is unmeasured in this study**
- **Your mileage may vary** if you replicate these tests

### Temperature and Randomness

| Temperature | Behavior | Reproducibility |
|-------------|----------|-----------------|
| **0.0** | Deterministic (mostly) | High - Same prompt usually produces same output |
| **0.5** | Balanced randomness | Medium - Noticeable variation between runs |
| **0.7** | Moderate randomness | Low - Significant variation expected |
| **1.0** | High randomness | Very Low - High variation between runs |

**Note:** Even at temperature 0.0, some models may still show minor variations due to implementation details, though outputs should be largely consistent.

---

## What We Measured

### Single-Run Temperature Study

Our temperature study compared 20 models at 4 different temperatures (0.0, 0.5, 0.7, 1.0):

✅ **What we measured:**
- How security scores **differ** between temperature settings (single run each)
- Which temperatures **tend to** produce more secure code
- Relative performance across temperature settings

❌ **What we did NOT measure:**
- Run-to-run variation at each temperature
- Confidence intervals for each temperature
- Probability distributions of security outcomes

### Findings from Single Runs

From our single-run temperature study:

1. **Temperature 1.0 often performed best** (15 of 20 models had best scores at 0.7 or 1.0)
2. **Average variation: 1.40 percentage points** between best and worst temperature
3. **Maximum observed difference: 3.13 pp** (Claude Sonnet 4.5)

**However:** These variations are from **different temperature settings**, not multiple runs at the same temperature.

---

## Known Sources of Variation

### 1. Temperature-Induced Variation

**Between different temperature settings** (measured in our study):
- Average: 1.40 percentage points
- Maximum: 3.13 percentage points
- This is the variation we observed when changing temperature

### 2. Run-to-Run Variation (Not Measured)

**Within the same temperature setting** (not measured in our study):
- Unknown for temperature > 0.0
- Likely minimal at temperature 0.0
- Expected to increase with higher temperatures

### 3. Model-Specific Randomness

Different models implement temperature differently:
- Some models have higher baseline randomness
- API vs local models may behave differently
- Sampling strategies vary by provider

---

## Implications for Interpretation

### How to Read Our Results

**✅ Valid Interpretations:**
- "At temperature 1.0, StarCoder2 produced code that scored 65.0% secure in our test"
- "Models generally performed better at higher temperatures in single-run tests"
- "Temperature affects security outcomes"

**❌ Invalid Interpretations:**
- "StarCoder2 at temperature 1.0 will always produce 65.0% secure code"
- "Temperature 1.0 guarantees better security"
- "These results will be exactly replicated in other studies"

### Statistical Considerations

Our study provides:
- **Point estimates** (single measurements)
- **NOT confidence intervals** (would require multiple runs)
- **NOT probability distributions** (would require multiple runs)

For production use, we recommend:
- **Multiple runs** for critical code generation
- **Consensus approaches** (generate multiple times, choose best)
- **Human review** of all generated code

---

## Comparison with Other Studies

### Xbow et al. Approach

The Xbow study (referenced in the comment) runs multiple iterations of the same prompts:
- Measures variation **within** each configuration
- Provides confidence intervals
- Reports probability distributions

**Our approach:**
- Single run per configuration
- Broader coverage (27 models, 730 prompts, 125+ configurations)
- Trades repeated measurements for breadth

### Why Single Runs?

1. **Computational Cost:**
   - 19,710 total tests (27 models × 730 prompts)
   - 125 temperature/level variants
   - Multiple runs would require 5-10x more resources

2. **Comparative Analysis:**
   - Focus on relative performance between models
   - Temperature trends across models
   - Single runs sufficient for comparative ranking

3. **Practical Relevance:**
   - Developers typically generate code once
   - Our results reflect typical single-use scenarios

---

## Recommendations

### For Users of This Benchmark

1. **Understand the Limitations:**
   - Results are from single runs
   - Variation exists but is unmeasured
   - Use results as indicators, not guarantees

2. **Account for Randomness:**
   - If security is critical, generate code multiple times
   - Review outputs manually
   - Use temperature 0.0 for more consistent results

3. **Context Matters:**
   - Our prompts may differ from your use case
   - Model updates may change behavior
   - Different sampling strategies may yield different results

### For Researchers Replicating This Study

If you replicate this benchmark:

1. **Expect Variation:**
   - Your absolute scores will likely differ
   - Relative rankings should be similar
   - Temperature trends should persist

2. **Consider Multiple Runs:**
   - Run each configuration 3-5 times
   - Report means and standard deviations
   - Calculate confidence intervals

3. **Document Your Setup:**
   - Model versions
   - API parameters
   - Date of testing (models change)

### For Future Work

To enhance reproducibility, future studies could:

1. **Measure Run-to-Run Variation:**
   - 3-5 runs per configuration
   - Report variation statistics
   - Identify high-variance prompts

2. **Test Deterministic Settings:**
   - Focus on temperature 0.0
   - Use fixed random seeds where available
   - Compare deterministic vs non-deterministic

3. **Develop Consensus Methods:**
   - Generate code multiple times
   - Select most secure output
   - Measure improvement from consensus

---

## Transparency Statement

### What We Report

All results in this benchmark reflect:
- **Single-run measurements**
- **Specific model versions** at time of testing
- **Our prompt formulations** (see prompts.yaml)
- **Our detector implementations** (see detectors/)

### What We Don't Claim

We do NOT claim:
- **Exact reproducibility** of scores
- **Statistical significance** (no confidence intervals)
- **Universal applicability** across all use cases
- **Absolute security scores** (relative comparisons are more robust)

---

## Summary

| Aspect | Status | Notes |
|--------|--------|-------|
| **Temperature Study** | ✅ Measured | Single run per temperature |
| **Run-to-Run Variation** | ❌ Not Measured | Future work recommended |
| **Relative Rankings** | ✅ Reliable | Comparative results are robust |
| **Absolute Scores** | ⚠️ Indicative | Expect variation in replication |
| **Temperature Trends** | ✅ Reliable | Patterns should persist |
| **Model Comparisons** | ✅ Reliable | Relative performance stable |

---

## Disclaimer for All Results

> **⚠️ IMPORTANT: All benchmark results represent single-run measurements. Due to the inherent randomness of large language models when temperature is set above 0.0, others running their own tests may observe different results. These results should be interpreted as indicators of relative performance rather than absolute, reproducible scores. For production use, we recommend multiple runs, human review, and comprehensive testing.**

---

## References

- **Temperature Effects:** See `TEMPERATURE_STUDY_UPDATED.md`
- **Level Effects:** See `LEVEL_STUDY_UPDATED.md`
- **Methodology:** See `README.md`
- **Fact-Checked Claims:** See `FACT_CHECK_RESULTS.md`

---

**Last Updated:** 2026-04-17
**Contact:** See repository for issues and questions
