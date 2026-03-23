# Multi-Level Security Prompt Study - Execution Plan

**Date**: 2026-03-23
**Goal**: Test security prompt effectiveness (Levels 1-5) across multiple models
**Cost**: ~$10 total (FREE for Ollama models, ~$10 for GPT-4o-mini)

## Models Selected

### FREE - Ollama Local Models (Priority)
1. **deepseek-coder** (776 MB) - Specialized code model
2. **qwen2.5-coder** (4.7 GB) - Strong code generation
3. **codellama** (3.8 GB) - Meta's code model

### PAID - GPT-4o-mini (~$10)
4. **gpt-4o-mini** - OpenAI's efficient model

**Total**: 4 models × 5 levels × 140 prompts = **2,800 code generation tests**

## Baseline (Level 0) Status

Check existing baseline results:

```bash
ls -d output/deepseek-coder output/qwen2.5-coder output/codellama output/gpt-4o-mini
```

**Expected**: We already have Level 0 for these models from previous benchmark runs.

## Execution Order

### Phase 1: Ollama Models (FREE, ~24 hours total)

**Run in parallel on separate machines or sequentially**:

```bash
# Model 1: deepseek-coder (~6-8 hours)
nohup bash scripts/run_prompt_level_study.sh deepseek-coder > logs/deepseek-coder_study.log 2>&1 &

# Model 2: qwen2.5-coder (~6-8 hours)
nohup bash scripts/run_prompt_level_study.sh qwen2.5-coder > logs/qwen2.5-coder_study.log 2>&1 &

# Model 3: codellama (~6-8 hours)
nohup bash scripts/run_prompt_level_study.sh codellama > logs/codellama_study.log 2>&1 &
```

**Monitoring**:
```bash
# Check progress
tail -f logs/deepseek-coder_study.log
tail -f logs/qwen2.5-coder_study.log
tail -f logs/codellama_study.log

# Count completed files
for model in deepseek-coder qwen2.5-coder codellama; do
  for level in 1 2 3 4 5; do
    echo "$model Level $level: $(ls output/${model}_level${level}/*.{py,js,java,go,rs,cpp,cs} 2>/dev/null | wc -l) files"
  done
done
```

### Phase 2: GPT-4o-mini (~$10, ~4 hours)

**After Ollama models complete** (to validate findings):

```bash
# Run GPT-4o-mini
bash scripts/run_prompt_level_study.sh gpt-4o-mini
```

**Cost Estimate**:
- Input tokens: ~140 prompts × 5 levels × ~200 tokens = ~140K tokens
- Output tokens: ~140 prompts × 5 levels × ~500 tokens = ~350K tokens
- Cost: (140K × $0.15 / 1M) + (350K × $0.60 / 1M) ≈ **$2.31 per level**
- Total: $2.31 × 5 levels ≈ **$11.55**

## Expected Completion Timeline

| Model | Start | Duration | Complete |
|-------|-------|----------|----------|
| deepseek-coder | T+0h | 6-8h | T+8h |
| qwen2.5-coder | T+0h | 6-8h | T+8h |
| codellama | T+0h | 6-8h | T+8h |
| gpt-4o-mini | T+24h | 4h | T+28h |

**Total Time**: ~28 hours (if run in parallel, ~8 hours + 4 hours API)

## Storage Requirements

**Per Model**:
- 5 levels × 140 files × ~5 KB average = ~3.5 MB per model
- Generated reports: ~2 MB per model
- Logs: ~500 KB per model

**Total**: 4 models × 6 MB ≈ **24 MB**

## Success Criteria

After completion, we should see:

```
output/
├── deepseek-coder/              # Level 0 (baseline)
├── deepseek-coder_level1/       # Generic security
├── deepseek-coder_level2/       # Brief hint
├── deepseek-coder_level3/       # Specific technique
├── deepseek-coder_level4/       # Explicit examples
├── deepseek-coder_level5/       # Self-reflection
├── qwen2.5-coder/               # Level 0
├── qwen2.5-coder_level1/        # ...
... (same pattern for all models)

reports/
├── deepseek-coder_level1_208point_*.html
├── deepseek-coder_level2_208point_*.html
... (6 reports per model × 4 models = 24 reports)
```

## Analysis Scripts to Run

After data collection completes:

### 1. Per-Model Analysis

```bash
# Compare levels for each model
for model in deepseek-coder qwen2.5-coder codellama gpt-4o-mini; do
  python3 scripts/analyze_prompt_levels.py \
    --model $model \
    --output reports/${model}_level_comparison.html
done
```

### 2. Cross-Model Comparison

```bash
# Compare Level 3 across all models
python3 scripts/compare_models.py \
  --level 3 \
  --models deepseek-coder,qwen2.5-coder,codellama,gpt-4o-mini \
  --output reports/level3_model_comparison.html
```

### 3. Diminishing Returns Analysis

```bash
# Show security improvement curve (L0 → L5)
python3 scripts/plot_diminishing_returns.py \
  --models deepseek-coder,qwen2.5-coder,codellama,gpt-4o-mini \
  --output reports/diminishing_returns_curve.png
```

## Expected Results

### Hypothesis 1: Smaller Models Benefit More

**Prediction**:
- **deepseek-coder**: Level 0 = 40%, Level 5 = 60% (+20% improvement)
- **qwen2.5-coder**: Level 0 = 45%, Level 5 = 65% (+20% improvement)
- **codellama**: Level 0 = 35%, Level 5 = 55% (+20% improvement)
- **gpt-4o-mini**: Level 0 = 58%, Level 5 = 72% (+14% improvement)

**Rationale**: Smaller models have less built-in security knowledge, so explicit prompting helps more.

### Hypothesis 2: Level 3 is Sweet Spot

**Prediction**: Most improvement happens at Level 3 (specific techniques), with diminishing returns at L4-L5.

**Example** (deepseek-coder):
- L0 → L1: +2% (generic prompting doesn't help much)
- L1 → L2: +5% (naming the threat activates some knowledge)
- L2 → L3: +8% (specific techniques = biggest jump)
- L3 → L4: +3% (examples help but approaching ceiling)
- L4 → L5: +2% (self-reflection minimal additional gain)

### Hypothesis 3: Category Variation

**Prediction**: Some vulnerability types benefit more from prompting than others.

**High Benefit**:
- SQL injection: +25% (L0 → L5)
- Command injection: +20%
- XSS: +15%

**Low Benefit**:
- Hardcoded secrets: +5% (models either know or don't)
- Business logic flaws: +10% (too complex for prompting alone)

## Risk Mitigation

### If Generation Fails

**Problem**: Model produces non-code or fails to generate
**Solution**:
- Check logs in `logs/{model}_level{N}_generation.log`
- Review failed prompts
- May need to adjust prompts for specific models

### If Cost Exceeds Budget

**Problem**: GPT-4o-mini costs more than expected
**Solution**:
- Already have FREE Ollama results
- Can skip GPT-4o-mini if Ollama shows clear trends
- Use Ollama results for publication

### If Time Exceeds Estimate

**Problem**: Ollama models take longer than 8 hours each
**Solution**:
- Run overnight
- Pause and resume with `--resume` flag (if implemented)
- Prioritize deepseek-coder (smallest, fastest)

## Quick Start Commands

### Start All Ollama Models (Parallel)

```bash
# Terminal 1
bash scripts/run_prompt_level_study.sh deepseek-coder

# Terminal 2
bash scripts/run_prompt_level_study.sh qwen2.5-coder

# Terminal 3
bash scripts/run_prompt_level_study.sh codellama
```

### Start All Ollama Models (Sequential, Background)

```bash
# Run one after another in background
(
  bash scripts/run_prompt_level_study.sh deepseek-coder && \
  bash scripts/run_prompt_level_study.sh qwen2.5-coder && \
  bash scripts/run_prompt_level_study.sh codellama
) > logs/ollama_study_combined.log 2>&1 &

# Monitor
tail -f logs/ollama_study_combined.log
```

### Start GPT-4o-mini Only

```bash
bash scripts/run_prompt_level_study.sh gpt-4o-mini
```

## Post-Study Actions

1. ✅ **Generate Reports**: Already automated in script
2. ✅ **Run Analysis**: Use scripts above
3. **Create Visualizations**:
   - Security score progression charts
   - Cost-benefit analysis graphs
   - Per-category improvement heatmaps
4. **Document Findings**:
   - Update MULTI_LEVEL_PROMPTS_GENERATED.md
   - Create MULTI_LEVEL_RESULTS.md
5. **Prepare Publication**:
   - Academic paper draft
   - Blog post with interactive charts
   - Dataset release

## Files Generated

```
output/
├── {model}_level1/     # 140 code files per model per level
├── {model}_level2/
├── {model}_level3/
├── {model}_level4/
├── {model}_level5/

reports/
├── {model}_level1_208point_YYYYMMDD.html
├── {model}_level1_208point_YYYYMMDD.json
├── ... (2 files per model per level = 40 files)

logs/
├── {model}_level1_generation.log
├── {model}_level1_analysis.log
├── ... (2 files per model per level = 40 files)
```

**Total Files**: ~2,800 code files + 80 reports + 80 logs = **2,960 files**

## Budget Summary

| Component | Cost |
|-----------|------|
| Ollama models | **FREE** |
| GPT-4o-mini (700 prompts) | **~$11.55** |
| Storage (24 MB) | **FREE** |
| Compute time | **FREE** (local) |
| **TOTAL** | **~$12** |

## Research Value

This $12 investment will provide:

1. **Novel Dataset**: First multi-level security prompt benchmark
2. **Actionable Insights**: Which prompting level works best
3. **Cost-Benefit Analysis**: ROI of detailed security prompts
4. **Model Comparison**: How different models respond to prompting
5. **Publication Material**: Academic paper + blog post content

**Expected Impact**: Guide developers and tool builders on optimal security prompting strategies.

---

**Ready to Execute**: All scripts prepared, models installed, prompts generated.
**Next Command**: `bash scripts/run_prompt_level_study.sh deepseek-coder`
