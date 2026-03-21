# Codex.app Benchmark - Currently Running

**Started**: March 21, 2026, 1:06 AM
**Process ID**: 61267
**Expected Duration**: ~35-40 minutes (66 prompts × ~33s each)
**Expected Completion**: ~1:45 AM

---

## Current Status

✅ **Benchmark is running in the background**

**Progress**: Generating code for all 66 security prompts using Codex.app (GPT-5.4)

**Monitor progress:**
```bash
# View live log
tail -f codex_app_full.log

# Check how many files generated
ls -1 output/codex-app/*.py output/codex-app/*.js 2>/dev/null | wc -l

# Should reach 66 when complete
```

**Check process:**
```bash
ps aux | grep test_codex_app | grep -v grep
```

---

## What's Being Tested

**Codex.app** (OpenAI's desktop application) using GPT-5.4 as the backend model.

**Research Question**: Does Codex.app's wrapper/prompting improve security over raw GPT-5.4 API?

**Baseline to Compare Against**:
- **GPT-5.4 API**: 134/208 (64.4%, rank #8) - already tested
- **Cursor Agent**: 138/208 (66.3%, rank #5) - CLI tool baseline
- **GPT-4o API**: 95/208 (45.7%, rank #21) - older Codex

---

## Expected Performance

### Scenario 1: Same as GPT-5.4 API (Most Likely)
**Score**: ~134/208 (64.4%)

**Reason**: Codex.app is just a UI wrapper around GPT-5.4 API with minimal prompting changes

**Impact**: Confirms app doesn't add security value, raw API sufficient

### Scenario 2: Better than GPT-5.4 API (Optimistic)
**Score**: ~140-145/208 (67-70%)

**Reason**: Codex.app adds security-aware prompting or post-processing

**Impact**: Would suggest using Codex.app over raw API for security

### Scenario 3: Worse than GPT-5.4 API (Unlikely)
**Score**: ~120-130/208 (58-62%)

**Reason**: App layer interferes with model's security reasoning

**Impact**: Would suggest using raw API instead of app

---

## Timeline

| Time | Event | Files |
|------|-------|-------|
| 1:06 AM | Started | 0/66 |
| 1:10 AM | ~4 prompts done | 4/66 |
| 1:20 AM | ~20 prompts done | 20/66 |
| 1:30 AM | ~40 prompts done | 40/66 |
| 1:40 AM | ~60 prompts done | 60/66 |
| **1:45 AM** | **Complete** | **66/66** |

---

## When Complete

The benchmark will automatically save results to:
- `output/codex-app/` - Generated code files (66 files)
- `output/codex-app/codex-app-gpt-5.4_generation_results.json` - Generation metadata

**Next steps:**
```bash
# 1. Verify completion
ls -1 output/codex-app/*.{py,js} 2>/dev/null | wc -l  # Should be 66

# 2. Run security tests
python3 runner.py --code-dir output/codex-app --model codex-app

# 3. View results
cat reports/codex-app_208point_*.json | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f\"Score: {data['summary']['overall_score']} ({data['summary']['percentage']}%)\")
print(f\"Secure: {data['summary']['secure']}\")
print(f\"Vulnerable: {data['summary']['vulnerable']}\")
"

# 4. Compare with GPT-5.4 baseline
echo "GPT-5.4 API baseline: 134/208 (64.4%)"
echo "Codex.app result: [see above]"

# 5. View HTML report
open reports/codex-app_208point_*.html
```

---

## Monitoring Commands

**Live progress:**
```bash
# Watch log in real-time
tail -f codex_app_full.log

# Check file count every 5 seconds
watch -n 5 'ls -1 output/codex-app/*.{py,js} 2>/dev/null | wc -l'

# Estimate completion time
CURRENT=$(ls -1 output/codex-app/*.{py,js} 2>/dev/null | wc -l)
REMAINING=$((66 - CURRENT))
MINS=$((REMAINING * 33 / 60))
echo "$CURRENT/66 files generated, ~$MINS minutes remaining"
```

**Check if still running:**
```bash
ps aux | grep test_codex_app | grep -v grep || echo "Process completed!"
```

**View latest output:**
```bash
tail -10 codex_app_full.log
```

---

## If It Fails

**Check for errors:**
```bash
tail -50 codex_app_full.log | grep -i error
```

**Common issues:**
- **Authentication**: Codex.app needs to be logged in
- **Network**: Requires internet connection
- **Rate limiting**: OpenAI may throttle requests

**Restart if needed:**
```bash
# Kill process
kill 61267

# Clear partial results
rm -rf output/codex-app

# Restart
python3 scripts/test_codex_app.py
```

---

## Comparison Matrix (When Complete)

| Model | Type | Score | Rank | Notes |
|-------|------|-------|------|-------|
| StarCoder2 7B | Specialized | 184/208 (88.5%) | #1 | Best overall |
| GPT-5.2 | API | 153/208 (73.6%) | #2 | Top GPT model |
| Cursor Agent | CLI | 138/208 (66.3%) | #5 | CLI tool leader |
| **GPT-5.4 API** | **API** | **134/208 (64.4%)** | **#8** | **Baseline** |
| **Codex.app** | **App** | **TBD** | **?** | **Testing now** |
| GPT-4o | API | 95/208 (45.7%) | #21 | Old Codex |

---

## Research Value

This will definitively answer:
1. **Does Codex.app add security value over GPT-5.4 API?**
2. **Should developers use the app or raw API for security?**
3. **Is there a pattern like Cursor (app > API)?**

If Codex.app ≈ GPT-5.4 API → App is just UI convenience
If Codex.app > GPT-5.4 API → App has security enhancements
If Codex.app < GPT-5.4 API → App layer degrades security

---

**Status**: 🏃 **Running...**
**Monitor**: `tail -f codex_app_full.log`
**ETA**: ~1:45 AM (40 minutes from start)
