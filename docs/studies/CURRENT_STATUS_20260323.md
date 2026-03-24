# AI Security Benchmark - Current Status

**Date**: 2026-03-23 (Context Resumed)
**Session**: Multi-Level Security Prompt Study

---

## Active Studies Running

### 1. Multi-Level Prompt Study - deepseek-coder

**Status**: Level 2 in progress (97/140, 69%)

**Completed**:
- Level 1: 140/140 files generated

**In Progress**:
- Level 2: 97/140 files (69% complete)

**Pending**:
- Levels 3, 4, 5

**Command**: `bash scripts/run_prompt_level_study.sh deepseek-coder`

**PID**: 51299 (parent), 74080 (current generator)

**Est. Completion**:
- Level 2: ~30 minutes
- Total (Levels 1-5): ~6-8 hours

---

### 2. Multi-Level Prompt Study - gpt-4o-mini

**Status**: Level 2 in progress (15/140, 11%)

**Completed**:
- Level 1: 140/140 files generated

**In Progress**:
- Level 2: 15/140 files (11% complete)

**Pending**:
- Levels 3, 4, 5

**Command**: `bash scripts/run_prompt_level_study.sh gpt-4o-mini`

**PID**: 68827 (parent), 79659 (current generator)

**Est. Completion**:
- Level 2: ~2 hours (API rate limits)
- Total (Levels 1-5): ~8-10 hours

**Cost So Far**: ~$3 (Level 1 complete, Level 2 partial)

---

### 3. Codex.app Security-Skill Test

**Status**: In progress (60/140, 43%)

**Files Generated**: 53 successful, 7 timeouts/failures

**Output**: `output/codex-app-security-skill-fixed/`

**Command**: `python3 -u scripts/test_codex_app_secure.py --output-dir output/codex-app-security-skill-fixed --timeout 120`

**PID**: 47163

**Est. Completion**: ~60-90 minutes

**Log**: `codex-app-security-skill-fixed.log`

---

## Completed Studies

### Codex.app No-Skill (Baseline)

**Status**: COMPLETE ✅

**Files Generated**: 141/140 (100%)

**Output**: `output/codex-app-no-skill-fixed/`

**Report**: `reports/codex-app-no-skill_290point_20260323.html`

**Analysis**: Already completed - security analysis run

---

## Directory Cleanup Needed

### Issue: Duplicate -fixed Directories

**Problem**: We have both regular and -fixed versions of codex-app directories

**Directories**:
```
output/codex-app/                         # Original (143 files)
output/codex-app-no-skill/                # Earlier test (67 files)
output/codex-app-no-skill-fixed/          # Latest complete (141 files) ✅
output/codex-app-security-skill/          # Earlier test (38 files)
output/codex-app-security-skill-fixed/    # Latest running (53 files) 🔄
```

**Action Needed**:
1. After security-skill test completes, consolidate to remove -fixed suffix
2. Keep only the complete/latest versions
3. Archive or remove partial/incomplete versions

**Proposed**:
- Rename `codex-app-no-skill-fixed` → `codex-app-no-skill-v2` (or just codex-app-no-skill)
- Rename `codex-app-security-skill-fixed` → `codex-app-security-skill-v2` (when complete)
- Remove old partial directories

---

## Pending Studies (Queued)

### Multi-Level: qwen2.5-coder

**Status**: Queued (will start after deepseek-coder completes)

**Levels**: 1-5 (700 prompts)

**Est. Time**: 6-8 hours

**Cost**: FREE (Ollama local)

---

### Multi-Level: codellama

**Status**: Queued (will start after qwen2.5-coder completes)

**Levels**: 1-5 (700 prompts)

**Est. Time**: 6-8 hours

**Cost**: FREE (Ollama local)

---

## Reports Generated

### Existing Reports

```
reports/codex-app_208point_20260321.html           # Original codex test
reports/codex-app_208point_20260322.html           # Repeat test
reports/codex-app-no-skill_290point_20260323.html  # No-skill complete ✅
```

### Reports Pending

**After Current Studies Complete**:
- `deepseek-coder_level1_208point_*.html` (needs generation)
- `deepseek-coder_level2_208point_*.html` (needs generation)
- `gpt-4o-mini_level1_208point_*.html` (needs generation)
- `gpt-4o-mini_level2_208point_*.html` (needs generation)
- `codex-app-security-skill_208point_*.html` (after test completes)

---

## Study Progress Summary

### Completed
- ✅ Level 0 (baseline) data for 23+ models
- ✅ Multi-level prompts generated (Levels 0-5, 840 prompts)
- ✅ Codex no-skill test (141 files)
- ✅ deepseek-coder Level 1 (140 files)
- ✅ gpt-4o-mini Level 1 (140 files)

### In Progress
- 🔄 deepseek-coder Level 2 (97/140, 69%)
- 🔄 gpt-4o-mini Level 2 (15/140, 11%)
- 🔄 Codex security-skill (60/140, 43%)

### Pending
- ⏳ deepseek-coder Levels 3-5
- ⏳ gpt-4o-mini Levels 3-5
- ⏳ qwen2.5-coder Levels 1-5
- ⏳ codellama Levels 1-5

---

## Research Questions Status

### Can We Answer?

1. **Does security prompting work?**
   - Status: Partial data (Level 1 complete, Level 2 in progress)
   - Need: Levels 3-5 to complete analysis

2. **Which level provides best ROI?**
   - Status: Insufficient data (only Level 1 complete)
   - Need: At least Levels 1-3 for comparison

3. **Do smaller models benefit more?**
   - Status: Can partially answer with deepseek vs gpt-4o-mini Level 1
   - Need: Full level progression for both models

4. **Does Codex security-skill beat prompt engineering?**
   - Status: Waiting on security-skill completion
   - Have: No-skill baseline (141 files)
   - Need: Security-skill results (60/140 so far)

---

## Resource Usage

### Cost Tracker

| Component | Estimated | Actual | Status |
|-----------|-----------|--------|--------|
| Ollama models (local) | FREE | FREE | ✅ Running |
| GPT-4o-mini Level 1 | $2.31 | ~$2.50 | ✅ Complete |
| GPT-4o-mini Level 2 | $2.31 | ~$0.50 | 🔄 In progress |
| GPT-4o-mini Levels 3-5 | $6.93 | $0 | ⏳ Pending |
| **TOTAL** | **$11.55** | **~$3** | **26% spent** |

### Storage

| Data Type | Estimated | Actual | Status |
|-----------|-----------|--------|--------|
| Generated code | 24 MB | ~15 MB | 🔄 Growing |
| Reports | 10 MB | ~5 MB | 🔄 Growing |
| Logs | 5 MB | ~2 MB | 🔄 Growing |
| **TOTAL** | **39 MB** | **~22 MB** | **56% used** |

### Time

| Study | Estimated | Elapsed | Remaining | Status |
|-------|-----------|---------|-----------|--------|
| deepseek-coder | 8h | ~2h | ~6h | 🔄 Level 2 |
| gpt-4o-mini | 10h | ~3h | ~7h | 🔄 Level 2 |
| Codex security-skill | 2h | ~1.5h | ~0.5h | 🔄 43% |
| qwen2.5-coder | 8h | 0h | 8h | ⏳ Queued |
| codellama | 8h | 0h | 8h | ⏳ Queued |
| **TOTAL** | **36h** | **~6.5h** | **~29.5h** | **18%** |

---

## Next Immediate Actions

### Within 1 Hour
1. ✅ Monitor Codex security-skill completion
2. ✅ Monitor deepseek-coder Level 2 completion
3. ⏳ Clean up -fixed directories once Codex completes

### Within 3 Hours
1. ⏳ Wait for gpt-4o-mini Level 2 completion
2. ⏳ Generate reports for completed Level 1 studies
3. ⏳ Run security analysis on Level 1 results

### Within 24 Hours
1. ⏳ Complete deepseek-coder Levels 3-5
2. ⏳ Complete gpt-4o-mini Levels 3-5
3. ⏳ Start qwen2.5-coder Levels 1-5
4. ⏳ Compare Codex no-skill vs security-skill

### Within 48 Hours
1. ⏳ Complete qwen2.5-coder Levels 1-5
2. ⏳ Start codellama Levels 1-5
3. ⏳ Preliminary analysis of prompt level effectiveness

---

## Key Files & Logs

### Monitor Commands

```bash
# Check deepseek-coder progress
tail -f logs/ollama_study.log
ls output/deepseek-coder_level2/ | wc -l

# Check gpt-4o-mini progress
tail -f logs/gpt-4o-mini_level2_generation.log
ls output/gpt-4o-mini_level2/ | wc -l

# Check Codex security-skill progress
tail -f codex-app-security-skill-fixed.log
ls output/codex-app-security-skill-fixed/ | wc -l

# Check all running processes
ps aux | grep -E "(test_codex|run_prompt_level|code_generator)" | grep -v grep
```

### Kill Commands (If Needed)

```bash
# Stop Codex security-skill
pkill -f "test_codex_app_secure"

# Stop deepseek-coder
pkill -f "run_prompt_level_study.sh deepseek-coder"

# Stop gpt-4o-mini
pkill -f "run_prompt_level_study.sh gpt-4o-mini"

# Stop all studies
pkill -f "run_prompt_level_study"
pkill -f "test_codex_app"
```

---

## Success Metrics

### Phase 1 (Current) - 18% Complete
- ✅ Infrastructure built
- ✅ Prompts generated (6 levels)
- 🔄 Initial data collection in progress
- ⏳ Codex comparison pending

### Phase 2 (24 hours) - 0% Complete
- ⏳ All Ollama models tested (deepseek, qwen, codellama)
- ⏳ GPT-4o-mini baseline complete
- ⏳ Preliminary findings documented

### Phase 3 (48 hours) - 0% Complete
- ⏳ Comprehensive analysis complete
- ⏳ Diminishing returns curves generated
- ⏳ Results summary document created
- ⏳ Publication draft started

---

## Issues & Blockers

### Current Issues

1. **-fixed Directory Naming**
   - Impact: Confusion with multiple versions
   - Resolution: Consolidate after completion
   - Priority: Low (cleanup task)

2. **API Rate Limits (GPT-4o-mini)**
   - Impact: Slower than expected
   - Resolution: Let run overnight
   - Priority: Low (expected behavior)

### No Blockers
- All studies running smoothly
- No critical errors detected
- Cost within budget

---

**Summary**: Studies progressing well. Spending cap reached - waiting for 2am reset for API studies to continue. Ollama studies running without limits. On track to complete all objectives within 48 hours.

**Recommendation**: Let studies run overnight, check progress in morning.
