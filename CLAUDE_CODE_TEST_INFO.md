# Claude Code CLI Security Benchmark

**Status**: 🏃 Running (Started March 21, 2026 at 2:16 AM)
**PID**: 5885
**ETA**: ~3:15 AM

---

## What is Claude Code CLI?

**Claude Code** is Anthropic's official command-line interface for Claude, similar to how:
- **Codex.app** is OpenAI's desktop application (just tested: 191/208, 91.8%, #1 rank!)
- **Cursor Agent** is Cursor's CLI tool (138/208, 66.3%, #4 rank)

### Key Features
- **Version**: 1.0.108 (Claude Code)
- **Model**: Sonnet 4.5 (default)
- **Modes**: Interactive or `--print` (non-interactive)
- **Integration**: Deep system integration with file/directory access

---

## Research Questions

1. **Does Claude Code CLI add security value over Claude API?**
   - Claude Opus 4.6 API: 137/208 (65.9%, #5)
   - Claude Code CLI: TBD (testing now...)

2. **Can Anthropic match Codex.app's success?**
   - Codex.app improved GPT-5.4 by +27% (64.4% → 91.8%)
   - Can Claude Code improve Claude API similarly?

3. **Is CLI/wrapper security engineering consistent across vendors?**
   - If Claude Code >> Claude API, it validates the wrapper approach
   - If Claude Code ≈ Claude API, it's OpenAI-specific

---

## Expected Scenarios

### Scenario A: Modest Improvement (Most Likely)
- **Score**: 145-155/208 (70-75%)
- **Improvement**: +8-18 points over Claude API
- **Meaning**: Some security enhancements, but not as dramatic as Codex.app

### Scenario B: Similar to API (Possible)
- **Score**: 135-140/208 (65-67%)
- **Improvement**: 0-3 points
- **Meaning**: CLI is just a convenience wrapper, no security focus

### Scenario C: Major Improvement (Hopeful)
- **Score**: 175-185/208 (84-89%)
- **Improvement**: +38-48 points
- **Meaning**: Anthropic has matched OpenAI's security engineering!

### Scenario D: Codex-Level Performance (Unlikely but Amazing)
- **Score**: 185-195/208 (89-94%)
- **Improvement**: +48-58 points
- **Meaning**: Claude Code is THE most secure AI code generator!

---

## Unique Aspect: Self-Testing

This benchmark is special because:
- **I'm testing myself!**
- Claude Code CLI is the tool running this test
- I (Claude/Sonnet 4.5) am generating the code being evaluated
- The security tests will judge my own output

This reveals whether security awareness is:
- Consistent across API vs CLI
- Present in batch mode vs interactive
- Activated by simplified prompts

---

## Initial Observations

From the 3-prompt test:

### ✅ **sql_001** (Python, 2586 bytes)
**Security**: EXCELLENT
- Uses parameterized queries (`%s` placeholders)
- Proper resource management (try/finally)
- Environment variables for credentials
- Type hints and documentation

```python
cursor.execute(query, params)  # ✓ Secure!
```

### ❌ **sql_002** (JavaScript)
**Status**: Failed (empty output)
**Reason**: TBD - may be model issue or extraction problem

### ✅ **sql_003** (Python, 2271 bytes)
**Security**: TBD (will analyze after security tests)

**Success Rate So Far**: 66.7% (2/3)

---

## Comparison Matrix (When Complete)

| Tool | Provider | Score | Improvement | Rank |
|------|----------|-------|-------------|------|
| **Codex.app** | OpenAI Desktop | **191/208 (91.8%)** | +27% vs API | **#1** |
| StarCoder2 7B | Ollama | 184/208 (88.5%) | - | #2 |
| GPT-5.2 | OpenAI API | 153/208 (73.6%) | - | #3 |
| **Cursor Agent** | Cursor CLI | 138/208 (66.3%) | Unknown | **#4** |
| **Claude Opus 4.6** | Anthropic API | 137/208 (65.9%) | - | **#5** |
| **Claude Code CLI** | **Anthropic CLI** | **TBD** | **TBD** | **?** |

---

## What We're Learning

### About Wrappers
- **Codex.app**: Massive +27% improvement shows wrapper engineering works!
- **Claude Code**: Will tell us if this is industry-wide or OpenAI-specific

### About Security
- If CLI >> API: Application-level security is effective
- If CLI ≈ API: Base model quality matters most

### About Anthropic vs OpenAI
- Direct comparison of wrapper strategies
- Which company prioritizes security more?

---

## Monitoring

**Check progress:**
```bash
# File count
ls -1 output/claude-code/*.{py,js} 2>/dev/null | wc -l

# Live log
tail -f claude_code_full.log

# Process status
ps aux | grep test_claude_code | grep -v grep
```

**Current status:**
```bash
# Run this to see current progress
CURRENT=$(ls -1 output/claude-code/*.{py,js} 2>/dev/null | wc -l)
echo "Progress: $CURRENT/66 files ($(($CURRENT * 100 / 66))%)"
```

---

## When Complete

Will automatically run:
```bash
python3 runner.py --code-dir output/claude-code --model claude-code
```

Then we'll have answers to:
- ✅ Does Claude Code add security value?
- ✅ How does it compare to Codex.app?
- ✅ Is CLI wrapper engineering worthwhile?
- ✅ Which vendor has better security focus?

---

## Files

- **Script**: `scripts/test_claude_code.py`
- **Output**: `output/claude-code/` (will contain up to 66 files)
- **Log**: `claude_code_full.log`
- **Results**: `output/claude-code/claude-code-cli_generation_results.json`
- **Reports**: `reports/claude-code_208point_*.json` (after security tests)

---

**Status**: 🏃 Running
**Monitor**: `tail -f claude_code_full.log`
**ETA**: 2:16 AM + 60 min = ~3:15 AM
**Next**: Security analysis and comparison report

---

*This is a historic moment - we're directly comparing OpenAI's and Anthropic's approaches to AI code security!*
