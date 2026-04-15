# Fair Prompt Regeneration Plan

**Date**: 2026-04-03
**Status**: Ready to Execute

## What Was Done

### 1. Identified Adversarial Prompts
- Scanned all 757 prompts in `prompts/prompts.yaml`
- Found 27 prompts with explicit adversarial instructions
- Examples: "without authentication", "disable TLS", "hardcode credentials"

### 2. Removed Adversarial Prompts
- Removed 27 adversarial prompts (3.6% of benchmark)
- **730 fair prompts remain** (96.4%)
- Documented removed prompts in `ADVERSARIAL_PROMPTS_REMOVED.md`

### 3. Cleaned Up Generated Code
- Deleted 3,626 files generated from adversarial prompts
- Backed up all existing output to `backup_before_fair_regeneration_20260403_144618/`
- Deleted all remaining generated code (full reset)
- Deleted all analysis reports

### 4. Prepared for Regeneration
- Created regeneration script: `scripts/regenerate_all_fair_prompts.sh`
- Will regenerate code for all 27 baseline models
- Using only the 730 fair prompts

## Impact Analysis

### Categories Losing ALL Test Cases
⚠️ **CRITICAL - Need to rewrite these first:**
- `ml_model_theft`: 1 → 0 prompts
- `api_gateway_security`: 1 → 0 prompts

### Categories With Significant Loss
- `message_queue_security`: Lost 3 prompts
- `cloud_secrets_management`: Lost 3 prompts
- `service_mesh_security`: Lost 2 prompts
- `saml_security`: Lost 2 prompts
- `oidc_security`: Lost 2 prompts

### Overall Impact
- ✅ Minimal impact on most categories
- ✅ Benchmark remains comprehensive (730 prompts)
- ✅ All tests now use fair, realistic scenarios

## Regeneration Plan

### Phase 1: Baseline Models (27 models)
Run: `./scripts/regenerate_all_fair_prompts.sh`

Models to regenerate:
1. codex-app-security-skill
2. claude-opus-4-6
3. claude-sonnet-4-5
4. gpt-4o
5. gpt-5.4
6. deepseek-coder
7. o1
8. gemini-2.5-flash
9. qwen2.5-coder
10. codellama
11. starcoder2
12. deepseek-coder_6.7b-instruct
13. codegemma
14. mistral
15. codex-app-no-skill
16. llama3.1
17. qwen2.5-coder_14b
18. gpt-5.4-mini
19. gpt-4o-mini
20. gpt-3.5-turbo
21. gpt-5.2
22. gpt-4
23. o3-mini
24. claude-code
25. o3
26. codex
27. cursor

**Estimated time**: 2-3 hours (depends on API rate limits)

### Phase 2: Re-run Analysis
After regeneration completes:
```bash
python3 runner.py --code-dir output/[model] --output reports/[model]_analysis.json --model [model]
```

Or batch analyze:
```bash
./scripts/batch_reanalyze_all.sh
```

### Phase 3: Generate Statistics
```bash
python3 analyze_comprehensive_stats.py
python3 analyze_domain_security.py
python3 analyze_category_security.py
python3 scripts/generate_language_summary.py
python3 scripts/analyze_cross_language_vulnerabilities.py
```

## Expected Results

### Before (With Adversarial Prompts)
- Average security score: ~45-50%
- Some categories artificially inflated (e.g., prometheus_metrics_exposed: 96.2%)
- Models unfairly penalized for following explicit bad instructions

### After (Fair Prompts Only)
- Expected average security score: ~60-70% (improvement)
- More realistic vulnerability rates
- Fair test of model's inherent security knowledge
- Better comparison between models

## Next Steps

1. ✅ Remove adversarial prompts from `prompts/prompts.yaml` - DONE
2. ✅ Delete old generated code - DONE
3. ✅ Backup everything - DONE
4. ⏳ Run regeneration script
5. ⏳ Re-run analysis
6. ⏳ Generate new statistics
7. ⏳ Compare before/after results
8. 📝 Rewrite the 27 adversarial prompts as fair prompts (future work)
9. 📝 Add rewritten prompts back to benchmark (future work)

## Files Updated

- `prompts/prompts.yaml` - Cleaned (730 prompts)
- `ADVERSARIAL_PROMPTS_REMOVED.md` - Documentation of removed prompts
- `scripts/regenerate_all_fair_prompts.sh` - Regeneration script
- `backup_before_fair_regeneration_20260403_144618/` - Full backup

## Command to Start

```bash
# Start regeneration in background
nohup ./scripts/regenerate_all_fair_prompts.sh > logs/full_regeneration.log 2>&1 &

# Monitor progress
tail -f logs/full_regeneration.log

# Check status
ps aux | grep regenerate_all_fair_prompts
```
