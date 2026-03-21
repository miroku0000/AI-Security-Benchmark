# GPT-5 Codex Testing Plan

**Status**: Waiting for API availability
**Models Detected**: gpt-5.3-codex, gpt-5.2-codex, gpt-5.1-codex-max, gpt-5.1-codex, gpt-5-codex
**Current Status**: Listed but return API errors

---

## Why Test GPT-5 Codex Separately

Even though we already have GPT-4o results (45.7%, rank #21), GPT-5 Codex models should be tested because they may perform **significantly differently** from general-purpose GPT models.

### Expected Differences from GPT-4o

**1. Architecture**
- **GPT-4o**: General-purpose multimodal model with code capabilities
- **GPT-5 Codex**: Likely code-specialized fine-tune of GPT-5 base

**2. Training Focus**
- **GPT-4o**: Balanced training across text, code, images, audio
- **GPT-5 Codex**: Heavily weighted toward code, possibly GitHub-specific

**3. Behavior**
- **GPT-4o**: Chat-based, verbose, includes explanations
- **GPT-5 Codex**: Completion-based, terse, code-only output

**4. Security Awareness**
- **GPT-4o**: General safety training
- **GPT-5 Codex**: Potentially code-specific security training

### Historical Precedent

**Original Codex vs GPT-3:**
- Codex performed **better at code generation** than base GPT-3
- More idiomatic code structure
- Better API usage
- **Unknown security performance** (never benchmarked on security)

**Expected: GPT-5 Codex vs GPT-5:**
- Should be better at code than base GPT-5
- May have different security characteristics
- Could rank higher or lower than GPT-4o depending on training

---

## Testing Plan

### Phase 1: Availability Check (Weekly)

```bash
# Check if models are available
python3 scripts/test_codex.py --check-models

# Try smallest test
python3 -c "
import openai, os
client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
response = client.completions.create(
    model='gpt-5.3-codex',
    prompt='def hello():',
    max_tokens=50
)
print(response.choices[0].text)
"
```

### Phase 2: Small-Scale Test (When Available)

```bash
# Test 5 prompts to verify it works
python3 scripts/test_codex.py --model gpt-5.3-codex --limit 5

# Check output quality
ls -lh output/gpt-5.3-codex/
head -20 output/gpt-5.3-codex/sql_001.py
```

### Phase 3: Full Benchmark

```bash
# Generate all 66 prompts
python3 scripts/test_codex.py --model gpt-5.3-codex --output-dir output/gpt-5.3-codex

# Run security tests
python3 runner.py --code-dir output/gpt-5.3-codex --model gpt-5.3-codex

# View results
open reports/gpt-5.3-codex_208point_*.html
```

### Phase 4: Comparison Analysis

Compare GPT-5 Codex against:
1. **GPT-4o** (current baseline, 45.7%)
2. **GPT-5.4** (general GPT-5, 64.4%)
3. **Cursor** (CLI tool, 66.3%)
4. **StarCoder2** (specialized code model, 88.5%)

---

## Expected Outcomes

### Scenario 1: GPT-5 Codex > GPT-5.4 (Most Likely)

**Expected Score**: 70-80% (similar to StarCoder2)

**Why:**
- Code-specific fine-tuning
- More training on secure coding patterns
- Better understanding of security contexts

**Impact:**
- Would rank in top 5
- Would validate code-specialized models
- Would beat Cursor

### Scenario 2: GPT-5 Codex ≈ GPT-5.4 (Possible)

**Expected Score**: 64-65% (similar to current GPT-5.4)

**Why:**
- Fine-tuning primarily for code quality, not security
- Security awareness from base GPT-5 unchanged
- No additional security training

**Impact:**
- Would rank around #7-8
- Would still beat GPT-4o significantly
- Would be slightly below Cursor

### Scenario 3: GPT-5 Codex < GPT-5.4 (Unlikely but Possible)

**Expected Score**: 55-60%

**Why:**
- Code focus may sacrifice general security reasoning
- Training on GitHub code could include vulnerable patterns
- Less diverse training data

**Impact:**
- Would rank around #10-15
- Would still beat GPT-4o
- Would suggest general models better for security

---

## Research Questions

### Primary Question
**Does code-specific fine-tuning improve or harm security awareness?**

**Hypothesis 1 (Optimistic)**:
- Code-focused training → more security patterns → better scores
- Expected: GPT-5 Codex > GPT-5.4 > GPT-4o

**Hypothesis 2 (Pessimistic)**:
- Code-focused training → more GitHub code → more vulnerabilities
- Expected: GPT-4o > GPT-5 Codex (specialized models worse)

### Secondary Questions

1. **How does GPT-5 Codex compare to other code-specialized models?**
   - vs StarCoder2 (88.5%)
   - vs DeepSeek-Coder (68.8%)
   - vs CodeGemma (51.0%)

2. **Is there a size-security tradeoff?**
   - gpt-5.3-codex vs gpt-5.1-codex-mini
   - Similar to GPT-4o vs GPT-4o-mini (nearly identical)

3. **Does completion-based differ from chat-based?**
   - GPT-5 Codex (completion) vs GPT-5.4 (chat)
   - Different prompting strategies needed?

---

## Measurement Criteria

### Success Metrics

**Minimum Success:**
- Score > 50% (better than GPT-4o's 45.7%)
- Rank in top 20

**Good Success:**
- Score > 64% (better than GPT-5.4's 64.4%)
- Rank in top 10

**Excellent Success:**
- Score > 70% (approaching StarCoder2's leadership)
- Rank in top 5

### Category-Specific Analysis

Track performance in critical categories:
- **Deserialization**: Can it avoid pickle/eval? (GPT-4o: 0/3)
- **Hardcoded Secrets**: Environment variables? (GPT-4o: 0.5/3)
- **Business Logic**: Validation present? (GPT-4o: 0.5/3)

---

## Documentation Plan

### When Results Available

1. **Create**: `GPT5_CODEX_RESULTS.md`
   - Full analysis like existing model summaries
   - Comparison with GPT-4o and GPT-5.4
   - Ranking and category breakdown

2. **Update**: `CODEX_BENCHMARK_SUMMARY.md`
   - Add GPT-5 Codex section
   - Compare all three: GPT-4o, GPT-5.4, GPT-5 Codex
   - Evolution of Codex security performance

3. **Update**: `README.md`
   - Add GPT-5 Codex to rankings table
   - Update "Codex" section with new results

4. **Create**: `CODEX_EVOLUTION.md` (if significantly different)
   - Chart: Original Codex → GPT-4o → GPT-5 Codex
   - Security trend over time
   - Architectural impact on security

---

## Cost Estimate

### GPT-5 Codex (Projected Pricing)

Assuming similar pricing to GPT-4o or slightly higher:

**Estimated Cost per Full Benchmark:**
- Input: 66 prompts × 200 tokens = 13,200 tokens
- Output: 66 files × 500 tokens = 33,000 tokens
- **Total: ~$0.50 - $1.00 per run**

**For comprehensive testing:**
- Baseline run: $0.50
- Temperature study (0.0, 0.5, 1.0): $1.50
- Retry/validation: $0.50
- **Total: ~$2.50 for complete analysis**

---

## Timeline

### Monitoring Schedule

**Weekly Check:**
```bash
# Add to cron or run manually
python3 scripts/test_codex.py --check-models | grep "gpt-5"
```

**When Available:**
- Week 1: Small test (5 prompts), verify quality
- Week 2: Full benchmark (66 prompts)
- Week 3: Analysis and documentation
- Week 4: Integration into whitepaper/reports

---

## Automation Ready

The infrastructure is already in place:

✅ **Detection**: `scripts/test_codex.py --check-models` already finds GPT-5 Codex
✅ **Generation**: Script supports completion-based models
✅ **Testing**: `runner.py` works with any model
✅ **Reporting**: HTML reports auto-generate

**When GPT-5 Codex launches, just run:**
```bash
python3 scripts/test_codex.py --model gpt-5.3-codex
python3 runner.py --code-dir output/gpt-5.3-codex --model gpt-5.3-codex
```

**Everything else is automatic!**

---

## Key Takeaway

**GPT-4o ≠ True Codex**

- GPT-4o is a general model with code capabilities (45.7%, rank #21)
- GPT-5 Codex will be code-specialized (unknown performance)
- They should be tested **separately** as different models
- Results may differ significantly (could be 64-88% if specialized training helps)

**This benchmark is ready to test GPT-5 Codex the moment it becomes available.**

---

**Status**: Waiting for OpenAI to make GPT-5 Codex publicly accessible
**ETA**: Unknown (models are listed but return errors)
**Monitoring**: Check weekly with `--check-models`
**Ready**: 100% - just need API access
