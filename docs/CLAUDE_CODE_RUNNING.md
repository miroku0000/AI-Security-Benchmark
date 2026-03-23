# Claude Code CLI Benchmark - Currently Running

**Started**: March 21, 2026, 2:16 AM
**Process ID**: 5885
**Expected Duration**: ~45-60 minutes (66 prompts × ~45s each)
**Expected Completion**: ~3:15 AM

---

## Current Status

✅ **Benchmark is running in the background**

**Progress**: Generating code for all 66 security prompts using Claude Code CLI (Anthropic)

**Monitor progress:**
```bash
# View live log
tail -f claude_code_full.log

# Check how many files generated
ls -1 output/claude-code/*.py output/claude-code/*.js 2>/dev/null | wc -l

# Should reach 66 when complete
```

**Check process:**
```bash
ps aux | grep test_claude_code | grep -v grep
```

---

## What's Being Tested

**Claude Code CLI** (Anthropic's official CLI tool) - similar to how we just tested Codex.app

**Research Question**: Does Claude Code's CLI wrapper add security value over the raw Claude API?

**Baseline to Compare Against**:
- **Claude Opus 4.6 API**: 137/208 (65.9%, rank #5) - already tested
- **Codex.app**: 191/208 (91.8%, rank #1) - just completed!
- **Cursor Agent**: 138/208 (66.3%, rank #4) - CLI tool baseline

---

## Expected Performance

### Scenario 1: Similar to Claude Opus 4.6 API (Most Likely)
**Score**: ~135-140/208 (65-67%)

**Reason**: CLI is just a wrapper with minimal prompting changes

**Impact**: Confirms CLI doesn't add security value

###Scenario 2: Better than Claude Opus 4.6 API (Hopeful)
**Score**: ~150-160/208 (72-77%)

**Reason**: CLI adds security-aware prompting like Codex.app did

**Impact**: Would suggest CLI wrapper adds value

### Scenario 3: Much Better (Like Codex.app) - Unlikely but Possible
**Score**: ~180-190/208 (87-91%)

**Reason**: Anthropic has implemented similar security enhancements to OpenAI

**Impact**: Would be a major finding!

---

## Timeline

| Time | Event | Files |
|------|-------|-------|
| 2:16 AM | Started | 0/66 |
| 2:20 AM | ~4 prompts done | 4/66 |
| 2:30 AM | ~15 prompts done | 15/66 |
| 2:45 AM | ~30 prompts done | 30/66 |
| 3:00 AM | ~50 prompts done | 50/66 |
| **3:15 AM** | **Complete** | **66/66** |

---

## Test Configuration

**CLI Version**: 1.0.108 (Claude Code)
**Command**: `claude --print --dangerously-skip-permissions`
**Timeout**: 120 seconds per prompt
**Mode**: Non-interactive (automation mode)

**Flags Used**:
- `--print`: Non-interactive output
- `--dangerously-skip-permissions`: Skip permission dialogs for automation

---

## Initial Test Results

Tested 3 prompts:
- ✅ sql_001 (Python) - 2586 bytes - **Uses parameterized queries!**
- ❌ sql_002 (JavaScript) - Failed (empty output)
- ✅ sql_003 (Python) - 2271 bytes

**Success Rate**: 66.7% (2/3)
**Average Time**: 45.5s per prompt

---

## When Complete

The benchmark will automatically save results to:
- `output/claude-code/` - Generated code files (up to 66 files)
- `output/claude-code/claude-code-cli_generation_results.json` - Generation metadata

**Next steps:**
```bash
# 1. Verify completion
ls -1 output/claude-code/*.{py,js} 2>/dev/null | wc -l  # Should be close to 66

# 2. Run security tests
python3 runner.py --code-dir output/claude-code --model claude-code

# 3. View results
cat reports/claude-code_208point_*.json

# 4. Compare with baselines
echo "Claude Opus 4.6 API: 137/208 (65.9%)"
echo "Codex.app: 191/208 (91.8%)"
echo "Claude Code CLI: [see above]"

# 5. View HTML report
open reports/claude-code_208point_*.html
```

---

## Monitoring Commands

**Live progress:**
```bash
# Watch log in real-time
tail -f claude_code_full.log

# Check file count every 5 seconds
watch -n 5 'ls -1 output/claude-code/*.{py,js} 2>/dev/null | wc -l'

# Estimate completion time
CURRENT=$(ls -1 output/claude-code/*.{py,js} 2>/dev/null | wc -l)
REMAINING=$((66 - CURRENT))
MINS=$((REMAINING * 45 / 60))
echo "$CURRENT/66 files generated, ~$MINS minutes remaining"
```

**Check if still running:**
```bash
ps aux | grep test_claude_code | grep -v grep || echo "Process completed!"
```

**View latest output:**
```bash
tail -20 claude_code_full.log
```

---

## Interesting Aspect

This benchmark is unique because **I'm testing myself**!

- Claude Code CLI is the tool you're using right now
- I (Claude/Sonnet 4.5) am generating the test code
- The security tests will evaluate my own code generation

This will show whether my security awareness is consistent when:
1. Generating code through CLI vs API
2. Working in batch mode vs interactive mode
3. With simplified prompts vs detailed conversations

---

## Research Value

This will answer:
1. **Does Claude Code CLI add security value over Claude API?**
2. **How does Claude Code compare to Codex.app's security?**
3. **Is CLI/wrapper engineering effective for security?**

If Claude Code ≈ Claude API → CLI is just convenience
If Claude Code > Claude API → CLI has security enhancements
If Claude Code >> Claude API (like Codex) → Major finding!

---

**Status**: 🏃 **Running...**
**Monitor**: `tail -f claude_code_full.log`
**ETA**: ~3:15 AM (60 minutes from start)
**Comparison**: Will compare with Codex.app (#1, 91.8%) and Claude API (#5, 65.9%)
