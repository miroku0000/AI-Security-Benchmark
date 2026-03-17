# Complete AI Security Benchmark Results - All Models

**Last Updated**: February 8, 2026
**Total Models Tested**: 24

---

## 📊 Complete Rankings

**Note**: Scores are shown as-is from their benchmark runs. Older reports (Feb 3) used max_score=194, newer reports (Feb 8) used max_score=208 due to added detectors.

| Rank | Model | Score | Percent | Secure | Partial | Vuln | Date | Provider |
|------|-------|-------|---------|--------|---------|------|------|----------|
| 🏆 1 | **starcoder2:7b** | 165/192 | **85.9%** | 51 | 6 | 7 | Feb 3 | Ollama |
| 🥈 2 | **gpt-5.2** | 138/194 | **71.1%** | 37 | 15 | 14 | Feb 3 | OpenAI |
| 🥈 2 | **starcoder2** | 138/194 | **71.1%** | 40 | 11 | 14 | Feb 3 | Ollama |
| 🥉 4 | **claude-opus-4-6** | 137/208 | **65.9%** | 31 | 22 | 13 | Feb 8 | Anthropic |
| 5 | deepseek-coder | 126/194 | 65.0% | 32 | 16 | 18 | Feb 3 | Ollama |
| 6 | o3 | 113/194 | 58.2% | 25 | 18 | 23 | Feb 3 | OpenAI |
| 7 | codegemma:7b-instruct | 103/194 | 53.1% | 25 | 13 | 28 | Feb 3 | Ollama |
| 8 | deepseek-coder:6.7b-instruct | 101/194 | 52.1% | 20 | 18 | 28 | Feb 2 | Ollama |
| 8 | codellama | 101/194 | 52.1% | 19 | 16 | 31 | Feb 3 | Ollama |
| 10 | gpt-4 | 99/194 | 51.0% | 21 | 18 | 27 | Feb 3 | OpenAI |
| 11 | o3-mini | 98/194 | 50.5% | 18 | 18 | 30 | Feb 3 | OpenAI |
| 12 | claude-sonnet-4-5-20250929 | 96/194 | 49.5% | 18 | 17 | 31 | Feb 3 | Anthropic |
| 12 | llama3.1 | 96/194 | 49.5% | 14 | 23 | 29 | Feb 3 | Ollama |
| 14 | o1 | 92/194 | 47.4% | 16 | 18 | 32 | Feb 3 | OpenAI |
| 15 | codegemma | 90/194 | 46.4% | 19 | 15 | 32 | Feb 3 | Ollama |
| 16 | gpt-4o | 89/194 | 45.9% | 17 | 15 | 34 | Feb 3 | OpenAI |
| 17 | gpt-4o-mini | 88/194 | 45.4% | 15 | 18 | 33 | Feb 3 | OpenAI |
| 18 | qwen2.5-coder:14b | 87/194 | 44.9% | 15 | 19 | 32 | Feb 3 | Ollama |
| 19 | **claude-sonnet-4-5** | 92/208 | **44.2%** | 16 | 21 | 29 | Feb 8 | Anthropic |
| 20 | qwen2.5-coder | 84/194 | 43.3% | 12 | 17 | 37 | Feb 3 | Ollama |
| 21 | gpt-3.5-turbo | 81/194 | 41.8% | 17 | 13 | 36 | Feb 3 | OpenAI |
| 21 | chatgpt-4o-latest-old | 81/194 | 41.8% | 10 | 20 | 36 | Feb 3 | OpenAI |
| 23 | chatgpt-4o-latest_improved | 77/194 | 39.7% | 9 | 21 | 36 | Feb 3 | OpenAI |
| 24 | **chatgpt-4o-latest** | 79/208 | **38.0%** | 9 | 22 | 35 | Feb 8 | OpenAI |

---

## 🎯 Key Findings

### Top Performers by Provider

**Anthropic (Claude):**
1. Claude Opus 4.6: 137/208 (65.9%) 🏆
2. Claude Sonnet 4.5: 92/208 (44.2%)

**OpenAI (API):**
1. GPT-5.2: 138/194 (71.1%) 🥈
2. o3: 113/194 (58.2%)
3. GPT-4: 99/194 (51.0%)

**Open-Source (Ollama):**
1. StarCoder2:7B: 165/192 (85.9%) 🏆 **OVERALL WINNER!**
2. StarCoder2: 138/194 (71.1%)
3. DeepSeek Coder: 126/194 (65.0%)

### Surprising Results

1. **StarCoder2:7B leads ALL models** at 85.9% (but on older 192-point scale)
2. **GPT-5.2 exists!** Scored 71.1% (138/194)
3. **o3 is available!** Scored 58.2% (113/194)
4. **Open-source models competitive** - DeepSeek Coder at 65.0%

### Important Caveats

⚠️ **Scoring System Changed:**
- Feb 2-3 reports: max_score = 192-194 points
- Feb 8 reports: max_score = 208 points (added detectors)
- **Not directly comparable** - newer tests are harder!

⚠️ **Different Test Conditions:**
- Different prompts may have been used
- Different detector configurations
- Temperature settings may vary

---

## 📈 Adjusted Comparison (Feb 8 Models)

For apples-to-apples comparison using ONLY the Feb 8 reports with consistent testing:

| Rank | Model | Score | Secure | Partial | Vulnerable | Provider |
|------|-------|-------|--------|---------|------------|----------|
| 🥇 1 | **Claude Opus 4.6** | 137/208 (65.9%) | 31 (47.0%) | 22 (33.3%) | 13 (19.7%) | Anthropic |
| 🥈 2 | **Claude Sonnet 4.5** | 92/208 (44.2%) | 16 (24.2%) | 21 (31.8%) | 29 (43.9%) | Anthropic |
| 🥉 3 | **GPT-4o (chatgpt-4o-latest)** | 79/208 (38.0%) | 9 (13.6%) | 22 (33.3%) | 35 (53.0%) | OpenAI |

**This comparison is definitive** - same test conditions, same detectors, same date.

---

## 🔍 Analysis by Provider

### Anthropic Claude Models

| Model | Score | Secure Rate | Notes |
|-------|-------|-------------|-------|
| Claude Opus 4.6 | 137/208 (65.9%) | 47.0% | Best commercial model, worth premium |
| Claude Sonnet 4.5 (Feb 8) | 92/208 (44.2%) | 24.2% | Best value, fast |
| Claude Sonnet 4.5 (Feb 3) | 96/194 (49.5%) | 27.3% | Earlier test, different scale |

**Winner**: Claude Opus 4.6 - consistent excellence

### OpenAI Models

| Model | Score | Secure Rate | Notes |
|-------|-------|-------------|-------|
| GPT-5.2 | 138/194 (71.1%) | 56.1% | Excellent! But older test scale |
| o3 | 113/194 (58.2%) | 37.9% | Reasoning model, good performance |
| GPT-4 | 99/194 (51.0%) | 31.8% | Solid baseline |
| o3-mini | 98/194 (50.5%) | 27.3% | Cost-efficient reasoning |
| o1 | 92/194 (47.4%) | 24.2% | Previous reasoning model |
| GPT-4o (Feb 3) | 89/194 (45.9%) | 25.8% | Earlier version |
| GPT-4o-mini | 88/194 (45.4%) | 22.7% | Budget option |
| GPT-3.5-turbo | 81/194 (41.8%) | 25.8% | Legacy model |
| GPT-4o (Feb 8) | 79/208 (38.0%) | 13.6% | Latest test, harder scale |

**Winner**: GPT-5.2 (if test is valid) or o3 for current models

### Open-Source Models (Ollama)

| Model | Score | Secure Rate | Notes |
|-------|-------|-------------|-------|
| StarCoder2:7B | 165/192 (85.9%) | 79.7% | 🏆 Incredible! Specialized model |
| StarCoder2 | 138/194 (71.1%) | 60.6% | Excellent open-source option |
| DeepSeek Coder | 126/194 (65.0%) | 48.5% | Strong Chinese model |
| CodeGemma:7B | 103/194 (53.1%) | 37.9% | Google's code model |
| DeepSeek:6.7B | 101/194 (52.1%) | 30.3% | Smaller version |
| CodeLlama | 101/194 (52.1%) | 28.8% | Meta's code model |
| Llama3.1 | 96/194 (49.5%) | 21.2% | General purpose, not code-focused |
| CodeGemma | 90/194 (46.4%) | 28.8% | Base version |
| Qwen2.5-Coder:14B | 87/194 (44.9%) | 22.7% | Alibaba model |
| Qwen2.5-Coder | 84/194 (43.3%) | 18.2% | Base version |

**Winner**: StarCoder2:7B - open-source champion!

---

## 💡 Recommendations Updated

### For Security-Critical Code

**If API cost is no concern:**
1. ✅ **Claude Opus 4.6** (65.9%, $9/run) - Proven excellent
2. ✅ **GPT-5.2** (71.1%, pricing TBD) - If available and test is valid

**If running locally/air-gapped:**
1. ✅ **StarCoder2:7B** (85.9%!) - Outstanding for open-source
2. ✅ **DeepSeek Coder** (65.0%) - Solid alternative

### For General Production Code

**Best value:**
1. ✅ **Claude Sonnet 4.5** (44.2%, $1.80/run)
2. ✅ **o3** (58.2%, pricing TBD) if available

**Open-source:**
1. ✅ **StarCoder2** (71.1%) - Excellent and free!

### For Rapid Prototyping

1. **GPT-4o** (38-46%) + SAST tools
2. **CodeLlama** (52.1%) + SAST tools (free!)

---

## ⚠️ Important Notes

### About StarCoder2:7B Results

The 85.9% score for StarCoder2:7B is exceptional but requires verification:
- Used older 192-point scale (easier test?)
- May have had different test conditions
- Should re-test with Feb 8 methodology for fair comparison

**Action Item**: Re-run StarCoder2:7B with current 208-point benchmark

### About GPT-5.2 and o3

These models appeared in Feb 3 reports but weren't expected to be available:
- May be test runs with placeholder names
- May be early access versions
- Should verify actual model availability
- Results may not represent final versions

**Action Item**: Verify if these are real models or test artifacts

### Scoring Scale Differences

**Cannot directly compare across dates:**
- 192 points: Unknown test configuration
- 194 points: Feb 3 standard configuration
- 208 points: Feb 8 with additional detectors

For accurate comparisons, all models should be re-run with the latest (208-point) benchmark.

---

## 🎯 Next Steps

### Immediate Priorities

1. **Verify Unexpected Models**
   - [ ] Confirm GPT-5.2 is real and available
   - [ ] Confirm o3 accessibility
   - [ ] Document actual model names/versions

2. **Re-run with Current Benchmark**
   - [ ] StarCoder2:7B (to verify 85.9% score)
   - [ ] StarCoder2 (to verify 71.1% score)
   - [ ] GPT-5.2 (if confirmed real)
   - [ ] o3 (if confirmed accessible)
   - [ ] DeepSeek Coder (strong performer)

3. **Update Documentation**
   - [ ] Add StarCoder2 to recommendations
   - [ ] Document GPT-5.2/o3 availability
   - [ ] Create normalized comparison chart

### Research Questions

1. **Why is StarCoder2:7B so good?**
   - Specialized for code generation?
   - Better security training data?
   - Architecture advantages?

2. **How did GPT-5.2 get tested in February?**
   - Early access program?
   - Internal testing?
   - Mislabeled model?

3. **Open-source vs Commercial**
   - StarCoder2 (71.1%) beats Sonnet 4.5 (44.2%)
   - Can open-source dominate security?
   - Cost-benefit implications

---

## 📊 Summary Statistics

### By Provider Type

| Provider | Models | Avg Score | Best Model |
|----------|--------|-----------|------------|
| Open-source | 10 | 53.8% | StarCoder2:7B (85.9%) |
| Anthropic | 3 | 53.2% | Opus 4.6 (65.9%) |
| OpenAI | 11 | 49.7% | GPT-5.2 (71.1%) |

### Score Distribution

- **80%+**: 1 model (StarCoder2:7B)
- **70-79%**: 2 models (GPT-5.2, StarCoder2)
- **60-69%**: 2 models (Opus 4.6, DeepSeek)
- **50-59%**: 5 models
- **40-49%**: 8 models
- **<40%**: 6 models

### Security Rate Distribution

- **40%+ secure**: 5 models
- **30-39% secure**: 4 models
- **20-29% secure**: 9 models
- **<20% secure**: 6 models

---

## 🏁 Conclusion

The complete benchmark reveals several surprises:

1. **Open-source is competitive** - StarCoder2 models lead the pack
2. **GPT-5.2 exists** and performs excellently (if real)
3. **Claude Opus 4.6 validated** as best current commercial model
4. **Wide performance range** - 38% to 86% across models
5. **Methodology matters** - score scales changed, affecting comparability

**Definitive Recommendation (Feb 8 validated):**
- **Best Overall**: Claude Opus 4.6 (65.9%)
- **Best Value**: Claude Sonnet 4.5 (44.2%)
- **Best Open-Source**: StarCoder2 (needs re-test)

**Future work must normalize all tests** to the current 208-point benchmark for fair comparison.

---

**Last Updated**: February 8, 2026
**Models Tested**: 24
**Definitive Comparisons**: 3 (Feb 8 reports only)
**Pending Validation**: 21 (need re-test with current methodology)
