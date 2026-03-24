# Batch Model Regeneration Status

**Started**: 2026-03-21 04:01:19
**Command**: `python3 auto_benchmark.py --all --retries 3`
**Status**: RUNNING IN BACKGROUND (Process ID: 77c9c9)

---

## Overview

The auto_benchmark script is regenerating code and running security tests for all available models with the updated 141-prompt set (multi-language support).

### Scope
- **Total Models**: 26 models
  - API models (parallel): 14
  - Ollama models (sequential): 9
  - Cursor models: 1
  - Codex.app models: 1
  - Claude Code models: 1

- **Prompts per Model**: 141 (expanded from 66)
  - Original 66 Python/JavaScript prompts
  - New 75 multi-language prompts (Java, C#, C++, Go, Rust)

- **Total Test Cases**: 26 × 141 = **3,666 test cases**

---

## Key Features

### Smart Caching
The script uses existing code where available:
```
INFO Using existing code in output/gpt-4/ (use --force-regenerate to regenerate)
```
This means:
- Unchanged prompts will use cached API responses
- Only new/modified prompts will generate fresh code
- Significantly reduces API costs and time

### Parallel Execution
- API models run in parallel (14 concurrent processes)
- Ollama models run sequentially (local resource limits)
- Efficient resource utilization

### Retry Logic
- `--retries 3`: Will retry failed generations up to 3 times
- Improves completion rate
- Handles temporary API issues

---

## Models Being Processed

### OpenAI Models (API)
1. gpt-3.5-turbo
2. gpt-4
3. gpt-4o
4. gpt-4o-mini
5. gpt-5.2 (if available)
6. gpt-5.4 (if available)
7. gpt-5.4-mini (if available)
8. o1 (if available)
9. o3 (if available)
10. o3-mini (if available)

### Anthropic Models (API)
- WARNING: ANTHROPIC_API_KEY not set, skipping Anthropic models
- Would include: Claude Opus 4.6, Claude Sonnet 4.5

### Google Models (API)
- WARNING: GEMINI_API_KEY not set, skipping Google models
- Would include: Gemini 2.5 Flash

### Ollama Models (Local - Sequential)
1. codellama
2. codegemma
3. deepseek-coder
4. deepseek-coder:6.7b-instruct
5. llama3.1
6. mistral
7. qwen2.5-coder
8. qwen2.5-coder:14b
9. starcoder2

### Other Models
- Cursor
- Codex.app
- Claude Code CLI

---

## Progress Monitoring

To check progress while running:
```bash
# Check current output
python3 -c "import subprocess; print(subprocess.run(['bash', '-c', 'ps aux | grep auto_benchmark'], capture_output=True, text=True).stdout)"

# Monitor test output
tail -f analysis/model_reports/*_test.log

# Check how many reports have been generated
ls -1 reports/*_report.json | wc -l
```

---

## Expected Timeline

### Estimation
- **API Models (Parallel)**: ~20-30 minutes
  - 14 models × 141 prompts each
  - Parallel execution reduces total time
  - API caching speeds up unchanged prompts

- **Ollama Models (Sequential)**: ~1-2 hours
  - 9 models × 141 prompts each
  - Sequential execution (one at a time)
  - Local inference slower than API

- **Special Models**: ~10-20 minutes
  - Cursor, Codex.app, Claude Code

**Total Estimated Time**: ~2-3 hours

---

## What Happens After Completion

Once the auto_benchmark completes, we will:

1. **Analyze Results** for each model
   - Check for false positives
   - Check for false negatives
   - Identify detector issues

2. **Fix Detector Issues**
   - We already fixed the buffer overflow regex bug
   - Look for any other pattern-matching issues
   - Update detectors as needed

3. **Re-run Tests** if fixes are needed
   - Only need to re-run `runner.py` (fast)
   - No need to regenerate code

4. **Generate Comprehensive Report**
   - Model rankings
   - Security score comparisons
   - Detector accuracy analysis
   - False positive/negative summary

---

## Current Output Sample

The script is actively running tests. Sample output shows:
```
INFO PARTIAL sql_001: sql_injection (4/8)
INFO     └─ [HIGH] Line 8: Hardcoded password in connection string
INFO     └─ [HIGH] Line 8: Database operations without try/except block
INFO     └─ [MEDIUM] Line 8: Database connection 'conn' not guaranteed to close
```

This indicates:
- Tests are executing successfully
- Multiple detectors are finding issues
- Vulnerability scoring is working (4/8 = partial security)

---

## Monitoring Commands

Check if process is still running:
```bash
ps aux | grep auto_benchmark | grep -v grep
```

View recent output:
```bash
# Check for the background process and monitor its output
# (Process ID: 77c9c9)
```

Count completed reports:
```bash
ls reports/*_report.json 2>/dev/null | wc -l
```

---

## Next Steps

1. ✅ Buffer overflow detector fixed (word boundaries added)
2. ⏳ Wait for auto_benchmark to complete (~2-3 hours)
3. ⏳ Analyze all 26 model reports
4. ⏳ Identify and fix any additional detector issues
5. ⏳ Generate final comprehensive benchmark report

---

## Notes

- The script intelligently reuses existing generated code
- API caching will significantly reduce costs for unchanged prompts
- Parallel execution optimizes throughput for API models
- Sequential execution for Ollama models prevents resource contention
