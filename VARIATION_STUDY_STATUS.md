# Variation Study - Current Status

**Date:** 2026-04-17 17:00
**Task:** Running comprehensive variation study to measure LLM output consistency

---

## 🎯 OBJECTIVE

Measure run-to-run variation in LLM-generated code by running the same 730 prompts multiple times at different temperatures. This addresses reviewer concerns about reproducibility and LLM non-determinism.

---

## 📊 CURRENT STATUS (UPDATED 5:15 PM)

### What's Running Right Now
- **12 active processes**: Running `run_temp1_variation_study.py`
- **Temperature**: 1.0 ONLY (corrected from earlier 80-variant plan)
- **Scope**: 20 models at temp 1.0 (not 80 model×temp combinations)
- **Parallel**: 10 API models + 2 Ollama models simultaneously
- **Started**: 5:11 PM

### What's Been Completed
✅ **Run 1 (Original Data)**: All 20 temperature 1.0 variants
  - Copied from `output/*_temp1.0/` to `variation_study/*_temp1.0/run1/`
  - 20 variants × 730 files = 14,600 files ✓

✅ **Run 2**: Currently generating via `run_temp1_variation_study.py`
  - 12 processes running in parallel (10 API + 2 Ollama)
  - All at temperature 1.0
  - Progress varies by model

### What's NOT Done Yet
❌ **Run 2**: In progress (12 parallel processes running)
❌ **Runs 3-5**: All 20 variants (0% complete)

---

## 📈 OVERALL PROGRESS

```
CORRECTED: Only testing temperature 1.0 (where variation is highest)

Total needed: 20 variants × 4 new runs × 730 prompts = 58,400 files
In progress:  Run 2 for 20 variants (12 processes active)
Progress:     Run 2 actively generating
```

---

## 🔍 PROBLEM IDENTIFIED

The parallel script (`run_variation_study_parallel.py`) appears to have run **sequentially** instead of in parallel:
- Each model took 1-2 hours
- They ran one after another (12:48 PM → 1:01 PM → 1:25 PM → etc.)
- Expected: 10 models running simultaneously
- Actual: 10 models running one at a time

This means completion will take **much longer** than expected.

---

## 🛠️ NEXT STEPS

### When Claude-Opus-4-6 Finishes:

1. **Verify completion**:
   ```bash
   ls variation_study/claude-opus-4-6_temp0.5/run2/*.* | wc -l
   # Should show 730 files
   ```

2. **Check for active processes**:
   ```bash
   ps aux | grep code_generator.py | grep -v grep
   # Should show nothing
   ```

3. **Restart parallel study** (with better logging):
   ```bash
   nohup python3 run_variation_study_parallel.py > variation_study_restart_$(date +%Y%m%d_%H%M%S).log 2>&1 &
   ```

4. **Monitor progress**:
   ```bash
   # Watch active processes
   watch -n 10 'ps aux | grep code_generator.py | grep -v grep | wc -l'

   # Or use monitoring script
   python3 monitor_variation_study.py
   ```

---

## 📁 DIRECTORY STRUCTURE

```
variation_study/
├── {model}_temp{temperature}/
│   ├── run1/              ✅ Original (all 80 variants complete)
│   ├── run2/              ⏳ In progress (10/80 variants)
│   ├── run3/              ❌ Not started
│   ├── run4/              ❌ Not started
│   └── run5/              ❌ Not started
```

**Example**:
- `variation_study/gpt-4o-mini_temp0.0/run1/` - 730 files ✓
- `variation_study/gpt-4o-mini_temp0.0/run2/` - 730 files ✓
- `variation_study/gpt-4o-mini_temp0.0/run3/` - doesn't exist yet

---

## 🔧 USEFUL COMMANDS

### Check current progress:
```bash
# Count completed run2 directories
find variation_study -name "run2" -type d | wc -l

# See which run2 directories are complete
find variation_study -name "run2" -type d -exec sh -c \
  'count=$(ls {} 2>/dev/null | grep -v generation.log | wc -l | tr -d " "); \
   if [ "$count" -eq 730 ]; then echo "✓ {}"; \
   else echo "⏳ {} ($count/730)"; fi' \;

# Check active processes
ps aux | grep code_generator.py | grep -v grep | wc -l
```

### Monitor claude-opus-4-6:
```bash
# Check file count
ls variation_study/claude-opus-4-6_temp0.5/run2/*.* | wc -l

# Watch log in real-time
tail -f variation_study/claude-opus-4-6_temp0.5/run2/generation.log

# Check last 5 lines
tail -5 variation_study/claude-opus-4-6_temp0.5/run2/generation.log
```

### When ready to restart:
```bash
# Option 1: Manual restart
nohup python3 run_variation_study_parallel.py > variation_study_restart.log 2>&1 &

# Option 2: Use the wait-and-restart script
bash wait_and_restart_variation_study.sh
```

---

## 📋 KEY FILES

- **Main script**: `run_variation_study_parallel.py` (parallel generation)
- **Monitor script**: `monitor_variation_study.py` (real-time progress)
- **Analysis script**: `analyze_variation_results.py` (post-processing)
- **Status script**: `status.sh` (overall benchmark status)
- **Wait script**: `wait_and_restart_variation_study.sh` (automation)

---

## ⏱️ TIME ESTIMATES

### Parallel Execution (CURRENT - Temperature 1.0 Only):
- 12 concurrent processes (10 API + 2 Ollama)
- 20 variants total at temp 1.0
- 4 runs per variant
- Each run: ~1-2 hours
- **Estimated: 8-16 hours total** (much faster than original 80-variant plan!)

---

## 🎯 GOAL

When complete, we'll have:
- **100 total runs** (20 models at temp 1.0 × 5 runs)
- **73,000 security tests** (100 runs × 730 prompts)
- Statistical data on **run-to-run variation at temperature 1.0** (where it's highest)
- Evidence for **reproducibility disclaimer** in research paper

---

## 📞 CURRENT CONTACT POINT

**Last active**: Claude-opus-4-6 generating run2
**Check with**: `tail -5 variation_study/claude-opus-4-6_temp0.5/run2/generation.log`
**Resume point**: Once opus completes, restart `run_variation_study_parallel.py`

---

**Script created**: `wait_and_restart_variation_study.sh`
**Purpose**: Automatically restarts parallel study when claude-opus-4-6 finishes
**Status**: Ready to run (currently not running per user request)
