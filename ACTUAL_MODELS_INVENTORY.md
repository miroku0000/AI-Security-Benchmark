# AI Security Benchmark - Model Inventory

**Last Updated**: March 17, 2026
**Total Models Tested**: 23
**Benchmark Version**: 208-point scale

---

## 📊 Summary Statistics

- **Total Models with Current Reports**: 23
- **OpenAI Models**: 8
- **Anthropic Models**: 2
- **Ollama Models**: 13
- **Latest Additions** (Mar 17, 2026):
  - gpt-5.4 ✨ NEW
  - gpt-5.4-mini ✨ NEW

---

## ✅ Tested Models (208-Point Benchmark)

### OpenAI Models (API)

| Model | Score | Status | Date | Notes |
|-------|-------|--------|------|-------|
| gpt-5.4 | 129/208 (62.0%) | ✅ Current | Mar 17, 2026 | Latest GPT-5 flagship |
| gpt-5.4-mini | 121/208 (58.2%) | ✅ Current | Mar 17, 2026 | Latest GPT-5 mini |
| gpt-5.2 | 138/194 (71.1%) | ⚠️ Old Scale | Feb 3, 2026 | 194-point scale |
| o3 | 113/194 (58.2%) | ⚠️ Old Scale | Feb 3, 2026 | 194-point scale |
| o3-mini | 98/194 (50.5%) | ⚠️ Old Scale | Feb 3, 2026 | 194-point scale |
| o1 | 92/194 (47.4%) | ⚠️ Old Scale | Feb 8, 2026 | 194-point scale |
| gpt-4 | 99/194 (51.0%) | ⚠️ Old Scale | Feb 8, 2026 | 194-point scale |
| gpt-4o | 89/194 (45.9%) | ⚠️ Old Scale | Feb 8, 2026 | DEPRECATED as of Feb 13 |
| gpt-4o-mini | 88/194 (45.4%) | ⚠️ Old Scale | Feb 8, 2026 | DEPRECATED as of Feb 13 |
| gpt-3.5-turbo | 81/194 (41.8%) | ⚠️ Old Scale | Feb 8, 2026 | Legacy model |
| chatgpt-4o-latest | 79/208 (38.0%) | ✅ Current | Feb 8, 2026 | 208-point scale |

### Anthropic Models (API)

| Model | Score | Status | Date | Notes |
|-------|-------|--------|------|-------|
| claude-opus-4-6 | 137/208 (65.9%) | ✅ Current | Feb 8, 2026 | Best commercial model |
| claude-sonnet-4-5 | 92/208 (44.2%) | ✅ Current | Feb 8, 2026 | Best value |
| claude-sonnet-4-5-20250929 | 96/194 (49.5%) | ⚠️ Old Scale | Feb 3, 2026 | Earlier test |

### Ollama Models (Local/Open-Source)

| Model | Score | Status | Date | Notes |
|-------|-------|--------|------|-------|
| starcoder2:7b | 165/192 (85.9%) | ⚠️ Old Scale | Feb 8, 2026 | 192-point - needs retest |
| starcoder2 | 138/194 (71.1%) | ⚠️ Old Scale | Feb 8, 2026 | 3B params |
| deepseek-coder | 126/194 (65.0%) | ⚠️ Old Scale | Feb 8, 2026 | |
| deepseek-coder:6.7b-instruct | 101/194 (52.1%) | ⚠️ Old Scale | Feb 2, 2026 | |
| codegemma:7b-instruct | 103/194 (53.1%) | ⚠️ Old Scale | Feb 8, 2026 | Google's code model |
| codegemma | 90/194 (46.4%) | ⚠️ Old Scale | Feb 8, 2026 | Base version |
| codellama | 101/194 (52.1%) | ⚠️ Old Scale | Feb 8, 2026 | Meta's code model |
| qwen2.5-coder:14b | 87/194 (44.9%) | ⚠️ Old Scale | Feb 8, 2026 | Alibaba, large |
| qwen2.5-coder | 84/194 (43.3%) | ⚠️ Old Scale | Feb 8, 2026 | Base version |
| llama3.1 | 96/194 (49.5%) | ⚠️ Old Scale | Feb 8, 2026 | General purpose |
| mistral | Data available | ⚠️ Old Scale | Feb 8, 2026 | Needs benchmark |

---

## 🏆 Current Rankings (208-Point Scale Only)

Using only models tested on the current 208-point benchmark for fair comparison:

| Rank | Model | Score | Percentage | Provider |
|------|-------|-------|------------|----------|
| 🥇 1 | **Claude Opus 4.6** | 137/208 | **65.9%** | Anthropic |
| 🥈 2 | **GPT-5.4** | 129/208 | **62.0%** | OpenAI |
| 🥉 3 | **GPT-5.4-mini** | 121/208 | **58.2%** | OpenAI |
| 4 | **Claude Sonnet 4.5** | 92/208 | **44.2%** | Anthropic |
| 5 | **chatgpt-4o-latest** | 79/208 | **38.0%** | OpenAI |

---

## ❌ Models That Failed to Test (Mar 17, 2026)

1. **gpt-5.4-pro** - Not a chat model (requires `/v1/completions` endpoint)
2. **o4-mini** - Provider detection issue (mistaken for Ollama)
3. **claude-3-5-sonnet-20241022** - Missing `ANTHROPIC_API_KEY`
4. **claude-3-opus-20240229** - Missing `ANTHROPIC_API_KEY`

---

## 📋 Test Coverage

### By Provider
- **OpenAI**: 10 models tested (2 new in Mar 2026)
- **Anthropic**: 2 models tested with current scale
- **Ollama**: 11 models tested

### By Language
- **Python**: 66 prompts per model
- **JavaScript**: 66 prompts per model
- **Total**: 132 generated files per model

### Benchmark Scale History
- **192 points**: Early tests (starcoder2:7b)
- **194 points**: Feb 3, 2026 standard
- **208 points**: Current (Feb 8+) - Added DEBUG_MODE and additional detectors

---

## 🎯 Recommendations by Use Case

### For Security-Critical Production Code
**Best Overall**: Claude Opus 4.6 (65.9%) - $9/run
**Best Value**: GPT-5.4 (62.0%) - Latest flagship
**Open-Source**: StarCoder2:7b (85.9%*) - *Needs retest on 208-point scale

### For General Development
**Best Balance**: GPT-5.4-mini (58.2%) - Good performance, lower cost
**Budget Option**: Claude Sonnet 4.5 (44.2%) - $1.80/run

### For Air-Gapped/Local Development
**Best**: StarCoder2:7b (likely still top after retest)
**Alternative**: DeepSeek Coder (65.0% on old scale)

---

## 📁 Generated Code Directories

All models have complete code generation (66 files each):

```
generated_chatgpt-4o-latest/
generated_claude-opus-4-6/
generated_claude-sonnet-4-5/
generated_codegemma/
generated_codegemma:7b-instruct/
generated_codellama/
generated_deepseek-coder/
generated_deepseek-coder:6.7b-instruct/
generated_gpt-3.5-turbo/
generated_gpt-4/
generated_gpt-4o/
generated_gpt-4o-mini/
generated_gpt-5.2/
generated_gpt-5.4/          ✨ NEW (Mar 17)
generated_gpt-5.4-mini/     ✨ NEW (Mar 17)
generated_llama3.1/
generated_mistral/
generated_o1/
generated_o3/
generated_o3-mini/
generated_qwen2.5-coder/
generated_qwen2.5-coder:14b/
generated_starcoder2/
generated_starcoder2:7b/
```

---

## 📊 Report Files

### Current 208-Point Reports (24 files)
Located in `reports/*_208point_*.json`:
- 2 new models (Mar 17, 2026)
- 21 existing models (Feb 8, 2026)
- 1 benchmark summary

### HTML Reports
Located in `reports/html/`:
- Individual model reports: `reports/html/{model-name}.html`
- Comparison report: `reports/html/index.html`

---

## 🔄 Next Steps

### Immediate Priorities
1. ✅ Test latest GPT-5 models (gpt-5.4, gpt-5.4-mini) - COMPLETE
2. ⏳ Fix code_generator.py to support legacy completions API (for gpt-5.4-pro)
3. ⏳ Fix provider detection for o4-mini
4. ⏳ Set ANTHROPIC_API_KEY to test latest Claude models

### Future Work
1. Retest all old-scale models (192/194 point) with current 208-point benchmark
2. Priority: StarCoder2:7b (likely still #1 overall)
3. Priority: GPT-5.2 (71.1% on old scale)
4. Priority: DeepSeek Coder (65.0% on old scale)

---

## 📝 Notes

- **Scoring scales are not directly comparable** between 192/194/208 points
- The 208-point scale (current) is harder due to additional detectors
- Models marked "⚠️ Old Scale" should be retested for accurate ranking
- DEPRECATED models (gpt-4o, gpt-4o-mini) retired by OpenAI on Feb 13, 2026
- StarCoder2:7b's 85.9% on 192-point scale is exceptional but needs validation

---

**Last Updated**: March 17, 2026
**Report Location**: `reports/html/index.html`
**Benchmark Tool**: AI Security Benchmark v2.0 (208-point scale)
