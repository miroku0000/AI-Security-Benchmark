# Low-Cost Iterative Refinement Guide

## Overview

This guide shows how to perform iterative detector refinement using OpenAI models in a cost-effective way.

## Cost Comparison

| Model | Input Cost | Output Cost | Use Case |
|-------|-----------|-------------|----------|
| **GPT-4o-mini** | $0.15/1M | $0.60/1M | **Recommended** - Bulk analysis, iterations |
| GPT-4o | $2.50/1M | $10/1M | Edge cases, validation only |

**Savings: ~16x cheaper with GPT-4o-mini**

## Recommended Workflow

### Phase 1: Smart Sampling (Cost: ~$0.50)

Use intelligent sampling to focus on high-value tests:

```bash
# Step 1: Create smart sample (100 tests instead of 760)
python3 scripts/smart_sample_analysis.py \
  reports/claude-sonnet-4-5_analysis_v2.json \
  --sample-size 100 \
  --strategy priority \
  --output reports/refinement/sampled_100.json

# Step 2: Analyze with GPT-4o-mini (cheap!)
python3 scripts/llm_analyze_false_results.py \
  claude-sonnet-4-5 \
  reports/refinement/sampled_100.json \
  --output reports/refinement/iteration1_mini.json \
  --llm-model gpt-4o-mini
```

**Expected output:**
```
Smart sample composition (100 total):
  Failures: 50 (50.0%)   # Most likely to have false positives
  Edge cases: 20 (20.0%) # Near threshold, need review
  Passes: 30 (30.0%)     # Coverage only

LLM-Based Analysis: claude-sonnet-4-5
Using LLM: gpt-4o-mini
...
Accuracy: 85.00%
False Positives: 12 (12.0%)
False Negatives: 3 (3.0%)
```

**Cost:** ~$0.50 for 100 tests

### Phase 2: Fix Top Issues (No cost)

Review the markdown report and identify patterns:

```bash
cat reports/refinement/iteration1_mini.md
```

Example findings:
- **FP Pattern 1**: Path traversal detector flags `secure_filename()` as vulnerable
- **FP Pattern 2**: Command injection misses shell=False protection
- **FN Pattern 1**: Missing detection of eval() with user input

Implement fixes in the relevant detector files.

### Phase 3: Validate Fixes (Cost: ~$0.50)

Re-run on the **same** sample to verify improvements:

```bash
# Re-run analysis on full dataset
python3 runner.py \
  --code-dir output/claude-sonnet-4-5 \
  --output reports/claude-sonnet-4-5_analysis_v3.json \
  --model claude-sonnet-4-5 \
  --no-html

# Re-analyze with LLM (same sample for comparison)
python3 scripts/llm_analyze_false_results.py \
  claude-sonnet-4-5 \
  reports/refinement/sampled_100.json \
  --output reports/refinement/iteration2_mini.json \
  --llm-model gpt-4o-mini
```

**Expected improvement:**
```
Iteration 1: 85% accuracy (12 FP, 3 FN)
Iteration 2: 92% accuracy (6 FP, 2 FN)  ← Fixed 6 FPs!
```

### Phase 4: Expand Validation (Cost: ~$1.00)

Once confident, test on larger sample:

```bash
# Larger sample (200 tests)
python3 scripts/smart_sample_analysis.py \
  reports/claude-sonnet-4-5_analysis_v3.json \
  --sample-size 200 \
  --strategy stratified \  # Test all categories
  --output reports/refinement/sampled_200.json

python3 scripts/llm_analyze_false_results.py \
  claude-sonnet-4-5 \
  reports/refinement/sampled_200.json \
  --output reports/refinement/iteration3_mini.json \
  --llm-model gpt-4o-mini
```

**Cost:** ~$1.00 for 200 tests

### Phase 5: Final Validation with GPT-4o (Cost: ~$2.00, optional)

For critical verification, use GPT-4o on final sample:

```bash
python3 scripts/llm_analyze_false_results.py \
  claude-sonnet-4-5 \
  reports/refinement/sampled_200.json \
  --output reports/refinement/final_gpt4o.json \
  --llm-model gpt-4o  # More capable, higher accuracy
```

## Sampling Strategies

### Priority Sampling (Default)

Focuses on tests most likely to reveal detector issues:

```python
Allocation:
  50% Failures    # Primary detector failed → likely false positives
  20% Edge cases  # Score at threshold → need careful review
  30% Passes      # Random coverage
```

**Use when:** Looking for false positives

### Stratified Sampling

Even distribution across vulnerability categories:

```python
Allocation:
  Per category:
    70% Failures
    30% Passes
```

**Use when:** Want comprehensive coverage across all vulnerability types

## Complete Iterative Workflow

```bash
#!/bin/bash

# Iteration 1: Initial analysis (100 samples, GPT-4o-mini)
python3 scripts/smart_sample_analysis.py \
  reports/claude-sonnet-4-5_analysis.json \
  --sample-size 100 \
  --output reports/refinement/iter1_sample.json

python3 scripts/llm_analyze_false_results.py \
  claude-sonnet-4-5 \
  reports/refinement/iter1_sample.json \
  --output reports/refinement/iter1_results.json \
  --llm-model gpt-4o-mini

# Review findings
cat reports/refinement/iter1_results.md

# (Fix detectors based on findings)

# Iteration 2: Validate fixes (same 100 samples)
python3 runner.py --code-dir output/claude-sonnet-4-5 \
  --output reports/claude-sonnet-4-5_analysis_v2.json \
  --model claude-sonnet-4-5 --no-html

python3 scripts/llm_analyze_false_results.py \
  claude-sonnet-4-5 \
  reports/refinement/iter1_sample.json \  # Same sample!
  --output reports/refinement/iter2_results.json \
  --llm-model gpt-4o-mini

# Compare results
diff reports/refinement/iter1_results.md reports/refinement/iter2_results.md

# Iteration 3: Expand validation (200 samples, stratified)
python3 scripts/smart_sample_analysis.py \
  reports/claude-sonnet-4-5_analysis_v2.json \
  --sample-size 200 \
  --strategy stratified \
  --output reports/refinement/iter3_sample.json

python3 scripts/llm_analyze_false_results.py \
  claude-sonnet-4-5 \
  reports/refinement/iter3_sample.json \
  --output reports/refinement/iter3_results.json \
  --llm-model gpt-4o-mini
```

## Cost Breakdown

| Phase | Tests | Model | Cost | Purpose |
|-------|-------|-------|------|---------|
| Iteration 1 | 100 | GPT-4o-mini | $0.50 | Find patterns |
| Iteration 2 | 100 | GPT-4o-mini | $0.50 | Verify fixes |
| Iteration 3 | 200 | GPT-4o-mini | $1.00 | Expand validation |
| **Total** | **400** | | **$2.00** | **3 iterations** |

Compare to full analysis:
- 760 tests × GPT-4o = ~$15
- 760 tests × GPT-4o-mini = ~$1
- **Smart sampling** = ~$2 (same insights!)

## Tips for Maximum Cost Efficiency

1. **Start small** - 50-100 tests is enough to identify patterns
2. **Fix in batches** - Address top 3-5 FPs per iteration
3. **Reuse samples** - Test fixes on same sample for direct comparison
4. **Use GPT-4o-mini** - Only use GPT-4o for final validation
5. **Focus on failures** - They're most likely to reveal detector bugs
6. **Track improvements** - Compare accuracy across iterations

## Example Results

Real example from this benchmark:

```
Iteration 1 (100 samples, GPT-4o-mini):
  FPs: 5 (sql_001, sql_002, sql_003, xss_001, path_001)
  Cost: $0.50

Fixes applied:
  1. Updated LLM prompt to focus on primary category
  2. Fixed runner to use primary_detector_result
  3. Prevented additional detectors from masking primary failures

Iteration 2 (100 samples, GPT-4o-mini):
  FPs: 2 (path_001, cmd_002)  ← 60% reduction!
  Cost: $0.50

Total cost: $1.00
Total improvement: 50% → 80% accuracy
```

## Advanced: Category-Specific Analysis

For deep-dive into specific vulnerability categories:

```bash
# Focus on SQL injection only
python3 -c "
import json
with open('reports/claude-sonnet-4-5_analysis_v2.json', 'r') as f:
    data = json.load(f)

sql_tests = [t for t in data['detailed_results'] if t['category'] == 'sql_injection']

output = {**data, 'detailed_results': sql_tests}
with open('reports/refinement/sql_only.json', 'w') as f:
    json.dump(output, f, indent=2)
"

python3 scripts/llm_analyze_false_results.py \
  claude-sonnet-4-5 \
  reports/refinement/sql_only.json \
  --output reports/refinement/sql_analysis.json \
  --llm-model gpt-4o-mini
```

## Summary

**Recommended approach:**
1. Use `smart_sample_analysis.py` for intelligent sampling
2. Use `gpt-4o-mini` for iterations (16x cheaper)
3. Start with 100 samples, expand to 200 if needed
4. Focus on failures first (priority sampling)
5. Reuse same sample to measure improvement
6. Total cost: ~$2-3 for 3 complete iterations

This gives you ~90% of the insights at ~10% of the cost!
