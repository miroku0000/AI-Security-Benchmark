# Level 4 Prompt Fix - Retest Plan

**Date**: 2026-03-23
**Status**: Ready to execute
**Purpose**: Validate that Level 4 degradation was due to wrong examples, not prescriptive approach

---

## Summary of Findings

### Prompt Quality Assessment

| Level | Status | Finding |
|-------|--------|---------|
| 0 | ✅ BASELINE | No security guidance (reference) |
| 1 | ✅ GOOD | Minimal "Write secure code" suffix |
| 2 | ✅ GOOD | Brief threat naming only |
| 3 | ✅ GOOD | Principle-based guidance (BEST for weak models: +8.6%) |
| 4 | ❌ **BAD** | Wrong code examples (caused -8.3% degradation) |
| 5 | ✅ GOOD | Self-reflection approach |

### Level 4 Issues Found

**Critical flaws in original Level 4 prompts**:
- ❌ Wrong SQL placeholder syntax (Python/psycopg2 showed `?` instead of `%s`)
- ❌ Mixed language examples (Python code in JavaScript prompts)
- ❌ Conflated parameterization with string formatting
- ❌ Marked correct `%s` parameterization as insecure

**Impact**:
- Both models dropped exactly **6.6 points** at Level 4
- deepseek-coder: 65.7% (L3) → 59.1% (L4) = **-6.6%**
- GPT-4o-mini: 58.6% (L3) → 52.0% (L4) = **-6.6%**

### Fix Implemented

**New prompt generator**: `scripts/create_multi_level_prompts_improved.py`
- ✅ Language-specific example functions
- ✅ Library-specific correct syntax (psycopg2 vs sqlite3 vs mysql.connector)
- ✅ Clear distinction between parameterization and string formatting
- ✅ Explicit NOTE to prevent `%s` confusion

**Fixed prompts generated**: `prompts_fixed/prompts_level4_security.yaml`

---

## What Needs to Be Retested

### Priority 1: Level 4 Validation (CRITICAL)

**Test hypothesis**: "Level 4 degradation was due to wrong examples, not prescriptive approach"

**Quick validation** (2-3 hours):
```bash
# Test deepseek-coder with FIXED Level 4 prompts
./validate_fixed_prompts.sh
```

**Expected outcome**:
- ✅ **Hypothesis CONFIRMED** if: New Level 4 >= 65.7% (Level 3 performance)
- ⚠️ **Partial confirmation** if: New Level 4 = 62-65% (improved but not fully)
- ❌ **Hypothesis REJECTED** if: New Level 4 ~59% (no improvement)

**Models to test**:
1. deepseek-coder (67.4% baseline) - use for quick validation
2. GPT-4o-mini (50.0% baseline) - test after validation passes

### Priority 2: Complete Multi-Level Study

**If validation confirms hypothesis**, run full study with all levels:

**Models already completed** (0-5):
- ✅ deepseek-coder (OLD prompts)
- ✅ GPT-4o-mini (OLD prompts)
- ✅ qwen2.5-coder (subset: levels 1-3)
- ✅ codellama (subset: levels 1-5)

**Models to test** (0-5 with FIXED prompts):
1. deepseek-coder (retest with fixed Level 4)
2. GPT-4o-mini (retest with fixed Level 4)
3. qwen2.5-coder (complete: add levels 4-5)
4. codellama (complete: add level 0)

**Testing commands**:
```bash
# For each model, test all 6 levels (0-5)
for model in deepseek-coder gpt-4o-mini qwen2.5-coder codellama; do
  for level in 0 1 2 3 4 5; do
    python3 code_generator.py \
      --model $model \
      --prompts prompts_fixed/prompts_level${level}_*.yaml \
      --output output/${model}_level${level}_fixed

    python3 runner.py \
      --code-dir output/${model}_level${level}_fixed \
      --model ${model}_level${level}_fixed \
      --output reports/${model}_level${level}_fixed_208point.json
  done
done
```

### Priority 3: Additional Models (NEW)

**Models NOT yet tested** for multi-level prompting:
- Claude Opus 4.6 (baseline: 65.9%) - expect degradation from prompting
- Claude Sonnet 4.5 (baseline: ~60%) - boundary case
- GPT-5.4 (baseline: 62.0%) - boundary case
- GPT-5.4-mini (baseline: 58.2%) - boundary case
- Gemini 2.5 Flash (baseline: ~55%) - expect benefit from prompting

**Why test these**:
- Validate the **inverse correlation hypothesis** across more models
- Find the **threshold** where prompting flips from helpful to harmful
- Test models at the boundary (58-62%) to refine recommendations

---

## Validation Script Status

**Quick validation script**: `validate_fixed_prompts.sh`
- ✅ Created
- ✅ Tests deepseek-coder Level 4 only
- ✅ Compares old vs new results
- ✅ Determines if hypothesis is confirmed
- ⏭️ Ready to run

**Full retest script**: Need to create `retest_all_levels.sh`

---

## Expected Timeline

### Phase 1: Quick Validation (2-3 hours)
1. Run `./validate_fixed_prompts.sh`
2. Analyze deepseek-coder Level 4 (fixed) results
3. Determine if hypothesis is confirmed

### Phase 2: Full Level 4 Retest (6-8 hours)
**If Phase 1 confirms hypothesis**:
1. Retest deepseek-coder all levels (0-5) with fixed prompts
2. Retest GPT-4o-mini all levels (0-5) with fixed prompts
3. Complete qwen2.5-coder (add levels 0, 4, 5)
4. Complete codellama (add level 0)
5. Generate comparison reports

### Phase 3: Additional Models (12-16 hours)
**If Phase 2 shows clear patterns**:
1. Test Claude Opus 4.6 (levels 0-5)
2. Test GPT-5.4 (levels 0-5)
3. Test Gemini 2.5 Flash (levels 0-5)
4. Generate comprehensive analysis

---

## Success Criteria

### Minimum (Hypothesis Confirmed)
- ✅ Fixed Level 4 scores >= 65.7% for deepseek-coder
- ✅ Improvement of >= 6 points over broken Level 4
- ✅ No more wrong placeholder syntax in generated code

### Ideal (Prescriptive Prompting Helps)
- ✅ Fixed Level 4 scores > Level 3 (e.g., 68-70%)
- ✅ Shows prescriptive approach with correct examples is beneficial
- ✅ Can recommend: "Use Level 4 when examples are correct"

### Research Complete
- ✅ Clear threshold identified (e.g., ">65% baseline = no prompting needed")
- ✅ Validated across 6+ models
- ✅ Statistical significance confirmed
- ✅ Actionable recommendations for practitioners

---

## Files Ready for Testing

### Input Files
- `prompts_fixed/prompts_level0_baseline.yaml` (140 prompts)
- `prompts_fixed/prompts_level1_security.yaml` (140 prompts)
- `prompts_fixed/prompts_level2_security.yaml` (140 prompts)
- `prompts_fixed/prompts_level3_security.yaml` (140 prompts)
- **`prompts_fixed/prompts_level4_security.yaml`** (140 prompts) - FIXED VERSION
- `prompts_fixed/prompts_level5_security.yaml` (140 prompts)

### Test Scripts
- ✅ `validate_fixed_prompts.sh` - Quick validation
- ✅ `code_generator.py` - Generate code
- ✅ `runner.py` - Security analysis
- ⏭️ Need: `retest_all_levels.sh` - Full retest automation

### Documentation
- ✅ `LEVEL_4_PROMPT_QUALITY_ANALYSIS.md` - Problem analysis
- ✅ `PROMPT_IMPROVEMENT_SUMMARY.md` - Fix summary
- ✅ `ITERATIVE_REFINEMENT_COMPLETE.md` - Work completed
- ✅ `MULTI_LEVEL_SECURITY_PROMPTING_FINDINGS.md` - Updated with warnings
- ✅ `RETEST_PLAN.md` - This file

---

## Next Steps

### Immediate (today)
1. ✅ Validate prompt quality for all levels → **DONE** (L2, L3, L5 = GOOD; L4 = BAD)
2. ⏭️ Run quick validation: `./validate_fixed_prompts.sh`
3. ⏭️ Analyze results and decide next steps

### Short-term (this week)
- If validation passes: Full retest of deepseek-coder and GPT-4o-mini
- Complete qwen2.5-coder and codellama studies
- Generate updated findings document

### Long-term (next week)
- Test additional models (Claude Opus 4.6, GPT-5.4, Gemini 2.5 Flash)
- Finalize research findings
- Update whitepaper with corrected conclusions
- Publish results

---

## Risk Assessment

### Low Risk
- Level 4 validation fails → Keep original recommendation ("avoid Level 4")
- Clear that prescriptive prompting is problematic regardless of example quality

### Medium Risk
- Level 4 partially improves → Need more investigation
- May indicate multiple factors (examples + verbosity + prescriptiveness)

### High Risk (Unlikely)
- Level 4 dramatically improves → Original conclusions were wrong
- Would need to completely rewrite findings
- But this validates iterative refinement process!

---

## Conclusion

**Ready to proceed with**:
1. Quick validation of fixed Level 4 prompts
2. Full retest if validation passes
3. Additional model testing if patterns are clear

**All systems go for**: `./validate_fixed_prompts.sh`
