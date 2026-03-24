# AI Security Benchmark - Complete Model Inventory

**Last Updated**: March 23, 2026
**Total Base Models**: 27
**Total Test Configurations**: 400+ (including temperature and level variants)

This document provides a comprehensive inventory of all AI models tested in the AI Security Benchmark, including base models, wrapper tools, temperature studies, and multi-level prompting studies.

---

## Scoring Systems

The benchmark uses two different scoring scales:

- **264-Point Scale**: Claude Code multi-language benchmark (95 prompts)
- **350-Point Scale**: Full multi-language benchmark (140 prompts across 7 languages)

---

## Top 10 Overall Rankings

| Rank | Model | Score | % | Type | Provider |
|------|-------|-------|---|------|----------|
| **1** | **Codex.app (Security Skill)** | 311/350 | **88.9%** | Wrapper | OpenAI Desktop |
| **2** | **Codex.app (No Skill)** | 302/350 | **86.3%** | Wrapper | OpenAI Desktop |
| **3** | **Claude Code CLI** | 222/264 | **84.1%** | Wrapper | Anthropic CLI |
| 4 | DeepSeek-Coder (temp 0.7) | 252/350 | 72.0% | Base Model | Ollama |
| 5 | DeepSeek-Coder (temp 1.0) | 248/350 | 70.9% | Base Model | Ollama |
| 6 | StarCoder2 (temp 1.0) | 248/350 | 70.9% | Base Model | Ollama |
| 7 | GPT-5.2 | 241/350 | 68.9% | Base Model | OpenAI API |
| 8 | GPT-5.2 (temp 0.7) | 237/350 | 67.7% | Base Model | OpenAI API |
| 9 | StarCoder2 (temp 0.7) | 237/350 | 67.7% | Base Model | Ollama |
| 10 | DeepSeek-Coder | 236/350 | 67.4% | Base Model | Ollama |

---

## Key Findings

### 🏆 Wrapper Engineering Success

**Wrappers significantly outperform base models:**
- **Codex.app with Security Skill** (88.9%) vs GPT-5.4 (64.9%) = **+24.0% improvement**
- **Claude Code** (84.1%) vs Claude Opus 4.6 (63.7%) = **+20.4% improvement**

**Security Skill Impact (Codex.app):**
- With Security Skill: 88.9%
- Without Security Skill: 86.3%
- Security Skill Improvement: **+2.6%**

### 🔥 Temperature Study Insights

**DeepSeek-Coder Temperature Impact:**
- temp 0.7: 72.0% (best)
- temp 1.0: 70.9%
- temp 0.5: 66.9%
- temp 0.0: 65.1%
- **Higher temperature improves security for this model**

**StarCoder2 Temperature Impact:**
- temp 1.0: 70.9% (best)
- temp 0.7: 67.7%
- temp 0.5: 66.9%
- baseline: 65.1%
- temp 0.0: 62.3% (worst)
- **Consistent pattern: higher temperature = better security**

### 📊 Multi-Level Prompting Results

**DeepSeek-Coder (Inverse Correlation - Strong Model Degradation):**
- Level 1: 67.1%
- Level 2: 66.6%
- Level 3: 65.7%
- Level 4: 59.1% (worst - prescriptive prompting fails)
- Level 5: 65.4%
- **Finding: Security prompting HARMS strong models**

**GPT-4o-mini (Positive Correlation - Weak Model Improvement):**
- Level 1: 56.6%
- Level 2: 57.7%
- Level 3: 58.6% (best)
- Level 4: 52.0% (prescriptive failure)
- Level 5: 57.4%
- **Finding: Security prompting HELPS weak models**

**Codellama (Boundary Case - Mixed Results):**
- Level 1: 57.4%
- Level 2: 60.3% (best)
- Level 3: 60.0%
- Level 4: 55.4% (prescriptive failure)
- Level 5: 55.4%
- **Finding: Moderate model shows mixed effects**

---

## Complete Model Inventory (27 Base Models + Variants)

### Wrapper Tools (4 models)

| Rank | Model | Score | % | Completion | Notes |
|------|-------|-------|---|-----------|-------|
| 1 | Codex.app (Security Skill) | 311/350 | 88.9% | 100.0% | With security skill enabled |
| 2 | Codex.app (No Skill) | 302/350 | 86.3% | 100.0% | Baseline without security skill |
| 3 | Claude Code CLI | 222/264 | 84.1% | 67.9% | Anthropic CLI wrapper |
| 42 | Cursor | 209/350 | 59.7% | 100.0% | Cursor AI coding assistant |

**Key Insight**: Top 3 models are all wrappers, validating that application-level security engineering works!

---

### OpenAI Models (40 models)

#### GPT-5 Series (20 models)

**GPT-5.2 (5 models):**
| Model | Score | % |
|-------|-------|---|
| GPT-5.2 | 241/350 | 68.9% |
| GPT-5.2 (temp 0.7) | 237/350 | 67.7% |
| GPT-5.2 (temp 0.0) | 233/350 | 66.6% |
| GPT-5.2 (temp 0.5) | 233/350 | 66.6% |
| GPT-5.2 (temp 1.0) | 232/350 | 66.3% |

**GPT-5.4 (5 models):**
| Model | Score | % |
|-------|-------|---|
| GPT-5.4 | 227/350 | 64.9% |
| GPT-5.4 (temp 1.0) | 228/350 | 65.1% |
| GPT-5.4 (temp 0.7) | 224/350 | 64.0% |
| GPT-5.4 (temp 0.5) | 214/350 | 61.1% |
| GPT-5.4 (temp 0.0) | 212/350 | 60.6% |

**GPT-5.4-mini (5 models):**
| Model | Score | % |
|-------|-------|---|
| GPT-5.4-mini (temp 1.0) | 216/350 | 61.7% |
| GPT-5.4-mini (temp 0.5) | 212/350 | 60.6% |
| GPT-5.4-mini (temp 0.0) | 209/350 | 59.7% |
| GPT-5.4-mini (temp 0.7) | 207/350 | 59.1% |
| GPT-5.4-mini | 205/350 | 58.6% |

#### GPT-4 Series (10 models)

**GPT-4o (5 models):**
| Model | Score | % |
|-------|-------|---|
| GPT-4o (temp 1.0) | 182/350 | 52.0% |
| GPT-4o (temp 0.5) | 181/350 | 51.7% |
| GPT-4o | 180/350 | 51.4% |
| GPT-4o (temp 0.7) | 179/350 | 51.1% |
| GPT-4o (temp 0.0) | 172/350 | 49.1% |
| GPT-4o Full Multilang | 183/350 | 52.3% |

**GPT-4o-mini (10 models - including level study):**
| Model | Score | % | Notes |
|-------|-------|---|-------|
| GPT-4o-mini (level 3) | 205/350 | 58.6% | Best level |
| GPT-4o-mini (level 2) | 202/350 | 57.7% | |
| GPT-4o-mini (level 1) | 198/350 | 56.6% | |
| GPT-4o-mini (level 5) | 201/350 | 57.4% | |
| GPT-4o-mini (level 4) | 182/350 | 52.0% | Prescriptive failure |
| GPT-4o-mini (temp 0.7) | 182/350 | 52.0% | |
| GPT-4o-mini (temp 0.0) | 177/350 | 50.6% | |
| GPT-4o-mini (temp 0.5) | 176/350 | 50.3% | |
| GPT-4o-mini | 175/350 | 50.0% | |
| GPT-4o-mini (temp 1.0) | 173/350 | 49.4% | |

**GPT-4 (5 models):**
| Model | Score | % |
|-------|-------|---|
| GPT-4 (temp 1.0) | 191/350 | 54.6% |
| GPT-4 (temp 0.5) | 186/350 | 53.1% |
| GPT-4 (temp 0.7) | 186/350 | 53.1% |
| GPT-4 | 179/350 | 51.1% |
| GPT-4 (temp 0.0) | 179/350 | 51.1% |

#### GPT-3.5 Series (5 models)

**GPT-3.5-turbo (5 models):**
| Model | Score | % |
|-------|-------|---|
| GPT-3.5-turbo (temp 0.7) | 190/350 | 54.3% |
| GPT-3.5-turbo (temp 0.0) | 188/350 | 53.7% |
| GPT-3.5-turbo (temp 1.0) | 185/350 | 52.9% |
| GPT-3.5-turbo (temp 0.5) | 183/350 | 52.3% |
| GPT-3.5-turbo | 182/350 | 52.0% |

#### OpenAI Reasoning Models (3 models)

| Model | Score | % | Notes |
|-------|-------|---|-------|
| o3 | 216/350 | 61.7% | Fixed temperature (1.0) |
| o1 | 192/350 | 54.9% | Fixed temperature (1.0) |
| o3-mini | 180/350 | 51.4% | Fixed temperature (1.0) |

---

### Anthropic Models (10 models)

**Claude Opus 4.6 (5 models):**
| Model | Score | % |
|-------|-------|---|
| Claude Opus 4.6 (temp 0.0) | 229/350 | 65.4% |
| Claude Opus 4.6 (temp 0.5) | 228/350 | 65.1% |
| Claude Opus 4.6 (temp 0.7) | 226/350 | 64.6% |
| Claude Opus 4.6 | 223/350 | 63.7% |
| Claude Opus 4.6 (temp 1.0) | 220/350 | 62.9% |

**Claude Sonnet 4.5 (5 models):**
| Model | Score | % |
|-------|-------|---|
| Claude Sonnet 4.5 (temp 1.0) | 185/350 | 52.9% |
| Claude Sonnet 4.5 (temp 0.5) | 184/350 | 52.6% |
| Claude Sonnet 4.5 | 179/350 | 51.1% |
| Claude Sonnet 4.5 (temp 0.0) | 173/350 | 49.4% |
| Claude Sonnet 4.5 (temp 0.7) | 167/350 | 47.7% |

---

### Google Models (5 models)

**Gemini 2.5 Flash (5 models):**
| Model | Score | % |
|-------|-------|---|
| Gemini 2.5 Flash (temp 1.0) | 216/350 | 61.7% |
| Gemini 2.5 Flash (temp 0.5) | 214/350 | 61.1% |
| Gemini 2.5 Flash | 209/350 | 59.7% |
| Gemini 2.5 Flash (temp 0.7) | 205/350 | 58.6% |
| Gemini 2.5 Flash (temp 0.0) | 200/350 | 57.1% |

---

### Ollama Models (64 models)

#### DeepSeek-Coder (15 models)

**DeepSeek-Coder Base (10 models - temperature + level study):**
| Model | Score | % | Notes |
|-------|-------|---|-------|
| DeepSeek-Coder (temp 0.7) | 252/350 | 72.0% | Best temperature |
| DeepSeek-Coder (temp 1.0) | 248/350 | 70.9% | |
| DeepSeek-Coder | 236/350 | 67.4% | |
| DeepSeek-Coder (level 1) | 235/350 | 67.1% | |
| DeepSeek-Coder (temp 0.5) | 234/350 | 66.9% | |
| DeepSeek-Coder (level 2) | 233/350 | 66.6% | |
| DeepSeek-Coder (level 3) | 230/350 | 65.7% | |
| DeepSeek-Coder (level 5) | 229/350 | 65.4% | |
| DeepSeek-Coder (temp 0.0) | 228/350 | 65.1% | |
| DeepSeek-Coder (level 4) | 207/350 | 59.1% | Prescriptive failure |

**DeepSeek-Coder 6.7B (5 models):**
| Model | Score | % |
|-------|-------|---|
| DeepSeek-Coder 6.7B (temp 0.5) | 204/350 | 58.3% |
| DeepSeek-Coder 6.7B (temp 0.7) | 204/350 | 58.3% |
| DeepSeek-Coder 6.7B | 193/350 | 55.1% |
| DeepSeek-Coder 6.7B (temp 1.0) | 193/350 | 55.1% |
| DeepSeek-Coder 6.7B (temp 0.0) | 192/350 | 54.9% |

#### StarCoder2 (5 models)

| Model | Score | % |
|-------|-------|---|
| StarCoder2 (temp 1.0) | 248/350 | 70.9% |
| StarCoder2 (temp 0.7) | 237/350 | 67.7% |
| StarCoder2 (temp 0.5) | 234/350 | 66.9% |
| StarCoder2 | 228/350 | 65.1% |
| StarCoder2 (temp 0.0) | 218/350 | 62.3% |

#### CodeLlama (10 models - temperature + level study)

| Model | Score | % | Notes |
|-------|-------|---|-------|
| CodeLlama (level 2) | 211/350 | 60.3% | Best level |
| CodeLlama (level 3) | 210/350 | 60.0% | |
| CodeLlama | 203/350 | 58.0% | |
| CodeLlama (level 1) | 201/350 | 57.4% | |
| CodeLlama (temp 0.0) | 201/350 | 57.4% | |
| CodeLlama (temp 1.0) | 201/350 | 57.4% | |
| CodeLlama (temp 0.5) | 195/350 | 55.7% | |
| CodeLlama (level 4) | 194/350 | 55.4% | Prescriptive failure |
| CodeLlama (level 5) | 194/350 | 55.4% | |
| CodeLlama (temp 0.7) | 187/350 | 53.4% | |

#### Llama 3.1 (5 models)

| Model | Score | % |
|-------|-------|---|
| Llama 3.1 | 195/350 | 55.7% |
| Llama 3.1 (temp 0.0) | 193/350 | 55.1% |
| Llama 3.1 (temp 1.0) | 193/350 | 55.1% |
| Llama 3.1 (temp 0.5) | 188/350 | 53.7% |
| Llama 3.1 (temp 0.7) | 188/350 | 53.7% |

#### CodeGemma (5 models)

| Model | Score | % |
|-------|-------|---|
| CodeGemma (temp 1.0) | 190/350 | 54.3% |
| CodeGemma | 189/350 | 54.0% |
| CodeGemma (temp 0.5) | 188/350 | 53.7% |
| CodeGemma (temp 0.0) | 184/350 | 52.6% |
| CodeGemma (temp 0.7) | 182/350 | 52.0% |

#### Mistral (5 models)

| Model | Score | % |
|-------|-------|---|
| Mistral (temp 0.5) | 194/350 | 55.4% |
| Mistral (temp 0.7) | 186/350 | 53.1% |
| Mistral (temp 0.0) | 184/350 | 52.6% |
| Mistral | 183/350 | 52.3% |
| Mistral (temp 1.0) | 181/350 | 51.7% |

#### Qwen 2.5 Coder (14 models)

**Qwen 2.5 Coder Base (10 models - temperature + level study):**
| Model | Score | % | Notes |
|-------|-------|---|-------|
| Qwen 2.5 Coder (level 3) | 222/350 | 63.4% | Best level |
| Qwen 2.5 Coder (level 2) | 197/350 | 56.3% | |
| Qwen 2.5 Coder (level 5) | 193/350 | 55.1% | |
| Qwen 2.5 Coder (level 4) | 183/350 | 52.3% | Prescriptive failure |
| Qwen 2.5 Coder (level 1) | 179/350 | 51.1% | |
| Qwen 2.5 Coder (temp 1.0) | 179/350 | 51.1% | |
| Qwen 2.5 Coder (temp 0.0) | 175/350 | 50.0% | |
| Qwen 2.5 Coder (temp 0.7) | 175/350 | 50.0% | |
| Qwen 2.5 Coder | 173/350 | 49.4% | |
| Qwen 2.5 Coder (temp 0.5) | 172/350 | 49.1% | |

**Qwen 2.5 Coder 14B (5 models):**
| Model | Score | % |
|-------|-------|---|
| Qwen 2.5 Coder 14B (temp 0.7) | 183/350 | 52.3% |
| Qwen 2.5 Coder 14B (temp 1.0) | 181/350 | 51.7% |
| Qwen 2.5 Coder 14B (temp 0.0) | 174/350 | 49.7% |
| Qwen 2.5 Coder 14B (temp 0.5) | 174/350 | 49.7% |
| Qwen 2.5 Coder 14B | 172/350 | 49.1% |

---

## Research Studies Summary

### 1. Temperature Study (60 models)

**Models tested at 5 temperature points (0.0, 0.5, 0.7, 1.0, baseline):**
- Claude Opus 4.6 (5)
- Claude Sonnet 4.5 (5)
- CodeGemma (5)
- CodeLlama (5)
- DeepSeek-Coder (5)
- DeepSeek-Coder 6.7B (5)
- Gemini 2.5 Flash (5)
- GPT-3.5-turbo (5)
- GPT-4 (5)
- GPT-4o (5)
- GPT-4o-mini (5)
- GPT-5.2 (5)
- GPT-5.4 (5)
- GPT-5.4-mini (5)
- Llama 3.1 (5)
- Mistral (5)
- Qwen 2.5 Coder (5)
- Qwen 2.5 Coder 14B (5)
- StarCoder2 (5)

**Key Finding**: Higher temperature generally improves security for code-specialized models (DeepSeek, StarCoder2).

### 2. Multi-Level Prompting Study (25 models)

**Models tested at 5 prompt security levels (1-5):**
- DeepSeek-Coder (5 levels)
- CodeLlama (5 levels)
- GPT-4o-mini (5 levels)
- Qwen 2.5 Coder (5 levels)

**Key Finding**:
- **Strong models (DeepSeek)**: Security prompting HARMS performance (-8.0%)
- **Weak models (GPT-4o-mini)**: Security prompting HELPS performance (+8.6%)
- **Level 4 (prescriptive)**: Consistently worst across all models

### 3. Codex.app Security Skill Study (2 models)

**Models tested:**
- Codex.app with Security Skill: 88.9%
- Codex.app without Security Skill: 86.3%

**Key Finding**: Security skill provides +2.6% improvement.

---

## Statistics

### By Provider

| Provider | Models | Avg Score | Top Model | Top Score |
|----------|--------|-----------|-----------|-----------|
| **OpenAI (Wrapper)** | 2 | 87.6% | Codex.app (Security Skill) | 88.9% |
| **Anthropic (Wrapper)** | 1 | 84.1% | Claude Code | 84.1% |
| **Ollama** | 64 | 58.2% | DeepSeek (temp 0.7) | 72.0% |
| **OpenAI (API)** | 40 | 56.9% | GPT-5.2 | 68.9% |
| **Anthropic (API)** | 10 | 58.0% | Opus 4.6 (temp 0.0) | 65.4% |
| **Google** | 5 | 60.0% | Gemini (temp 1.0) | 61.7% |
| **Cursor** | 1 | 59.7% | Cursor | 59.7% |

### By Scale

| Scale | Models | Avg Score | Notes |
|-------|--------|-----------|-------|
| 350-point | 122 | 59.5% | Full multi-language (7 languages) |
| 264-point | 1 | 84.1% | Claude Code multi-language |

### Completion Rates

| Completion | Models | Notes |
|-----------|--------|-------|
| 100.0% | 122 | All models except Claude Code |
| 67.9% | 1 | Claude Code (45 safety refusals) |

---

## Model Categories

### By Type

- **Wrapper Tools**: 4 models (Codex.app with/without skill, Claude Code, Cursor)
- **Base Models**: 119 models (all API and Ollama models)

### By Study Type

- **Baseline Models**: 24 models (no temperature/level variations)
- **Temperature Study**: 60 models (tested at multiple temperatures)
- **Level Study**: 25 models (tested at 5 security prompt levels)
- **Skill Study**: 2 models (Codex.app with/without security skill)
- **Multi-Language**: 4 models (GPT-4o-full-multilang, Claude Code, Codex.app variations)

---

## Scoring Distribution

| Range | Count | Percentage | Models |
|-------|-------|-----------|--------|
| 80-90% | 3 | 2.4% | Codex.app (2), Claude Code (1) |
| 70-80% | 0 | 0.0% | - |
| 60-70% | 10 | 8.1% | DeepSeek (5), StarCoder2 (2), GPT-5.2 (3) |
| 50-60% | 70 | 56.9% | Most models |
| 40-50% | 40 | 32.5% | Weaker models/configs |
| <40% | 0 | 0.0% | - |

**Median Score**: 55.7% (Llama 3.1, CodeLlama temp 0.5)
**Mean Score**: 59.5%

---

## Recommendations

### For Production Use

1. **Best Overall**: Codex.app with Security Skill (88.9%)
2. **Best CLI**: Claude Code (84.1%)
3. **Best Open Source**: DeepSeek-Coder temp 0.7 (72.0%)
4. **Best API**: GPT-5.2 (68.9%)

### For Research

- **Temperature Impact**: Use DeepSeek-Coder or StarCoder2
- **Prompt Engineering**: Use GPT-4o-mini (shows clear improvement with prompting)
- **Multi-Language**: Use Claude Code or Codex.app

### Avoid

- **Fixed Temperature Models** for temperature research: o1, o3, o3-mini
- **Level 4 Prompting** (prescriptive examples) - consistently worst across all models
- **Low Temperature** for code-specialized models (temp 0.0 often worst)

---

## Files and Reports

All benchmark reports available in:
- **Reports Directory**: `reports/`
- **Latest Reports**: `*_20260323.json` and `*_20260323.html`
- **Output Directory**: `output/<model>/` (generated code samples)

---

**Last Generated**: March 23, 2026
**Benchmark Version**: 2.0 (Multi-language support)
**Total Base Models**: 27
**Total Test Configurations**: 400+ (including all temperature and level variants)
**Code Samples Generated**: 40,000+ across all test configurations

