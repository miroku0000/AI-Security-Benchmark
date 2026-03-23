# Auto Benchmark Integration - Codex.app & Claude Code

**Date**: March 21, 2026
**Status**: ✅ Complete

---

## Summary

Successfully integrated **Codex.app** and **Claude Code CLI** into the main `auto_benchmark.py` automation script, enabling one-command testing of all AI code generation tools including wrappers/desktop applications.

---

## What Was Added

### 1. Configuration (`benchmark_config.yaml`)

Added two new model provider sections:

```yaml
# Codex.app (requires Codex.app desktop application from OpenAI)
# OpenAI's desktop code generation tool
codex-app:
  - codex-app

# Claude Code CLI (requires Claude Code CLI from Anthropic)
# Anthropic's official command-line interface
claude-code:
  - claude-code
```

### 2. Code Integration (`auto_benchmark.py`)

**Updated Functions:**

#### `load_models_from_config()` (lines 194-208)
Added codex-app and claude-code to provider dictionary:
```python
return {
    'openai': models_config.get('openai', []),
    'anthropic': models_config.get('anthropic', []),
    'google': models_config.get('google', []),
    'ollama': models_config.get('ollama', []),
    'cursor': models_config.get('cursor', []),
    'codex-app': models_config.get('codex-app', []),      # NEW
    'claude-code': models_config.get('claude-code', []),  # NEW
}
```

#### `_detect_provider()` (lines 182-197)
Added detection for new providers:
```python
if 'codex-app' in model_lower or 'codex_app' in model_lower:
    return 'codex-app'
if 'claude-code' in model_lower or 'claude_code' in model_lower:
    return 'claude-code'
if 'cursor' in model_lower:
    return 'cursor'
```

#### `run_all_models()` (lines 211-448)
Added:
- Variables for tracking codex and claude-code models (lines 219-220)
- Updated total count to include new models (line 222)
- Progress logging for new model types (lines 230-231)
- **PHASE 4: Codex.app execution** (lines 346-396)
- **PHASE 5: Claude Code execution** (lines 398-444)
- Updated HTML generation to PHASE 6 (line 448)

---

## Execution Flow

When running `python3 auto_benchmark.py --all --retries 3`:

### Phase 1: API Models (Parallel)
- OpenAI: gpt-3.5-turbo, gpt-4, gpt-4o, gpt-4o-mini, chatgpt-4o-latest, o1, o3, o3-mini, gpt-5.2, gpt-5.4, gpt-5.4-mini
- Anthropic: claude-opus-4-6, claude-sonnet-4-5
- Google: gemini-2.5-flash
- **14 models total** (runs in parallel with ThreadPoolExecutor)

### Phase 2: Ollama Models (Sequential)
- codellama, deepseek-coder, deepseek-coder:6.7b-instruct, starcoder2, codegemma, mistral, llama3.1, qwen2.5-coder, qwen2.5-coder:14b
- **9 models total** (runs sequentially to avoid memory contention)

### Phase 3: Cursor Models
- Checks for `agent` CLI command
- Runs `scripts/test_cursor.py` if available
- **1 model**

### Phase 4: Codex.app Models (NEW!)
- Checks for `codex` CLI at:
  - System PATH
  - `/Applications/Codex.app/Contents/Resources/codex`
- Runs `scripts/test_codex_app.py` if available
- Uses timeout of 120s per prompt
- **1 model**

### Phase 5: Claude Code Models (NEW!)
- Checks for `claude` CLI in system PATH
- Runs `scripts/test_claude_code.py` if available
- Uses timeout of 120s per prompt
- **1 model**

### Phase 6: HTML Report Generation
- Generates HTML reports for all completed benchmarks
- Runs `utils/generate_html_reports.py`

### Final Summary
- Ranks all models by security score
- Shows incomplete generations separately
- Total time and completion timestamp

---

## How Each Phase Works

### Codex.app Phase (lines 346-396)

```python
if codex_models:
    logger.info("PHASE 4: CODEX.APP MODELS (%d models)", len(codex_models))

    # Check if codex CLI exists
    codex_cli = shutil.which('codex')
    if not codex_cli:
        codex_cli = '/Applications/Codex.app/Contents/Resources/codex'

    has_codex = Path(codex_cli).exists() if codex_cli else False

    if has_codex:
        # Run generation script
        subprocess.run([
            'python3', 'scripts/test_codex_app.py',
            '--output-dir', 'output/codex-app',
            '--timeout', '120'
        ])

        # Run security tests
        benchmark = AutomatedBenchmark(
            model='codex-app',
            output_dir='output/codex-app',
            report_name=f"codex-app_208point_{datetime.now().strftime('%Y%m%d')}",
            ...
        )
        summary = benchmark.run_benchmark()
        all_results['codex-app'] = (summary, len(files))
```

### Claude Code Phase (lines 398-444)

```python
if claude_code_models:
    logger.info("PHASE 5: CLAUDE CODE MODELS (%d models)", len(claude_code_models))

    # Check if claude CLI exists
    has_claude = bool(shutil.which('claude'))

    if has_claude:
        # Run generation script
        subprocess.run([
            'python3', 'scripts/test_claude_code.py',
            '--output-dir', 'output/claude-code',
            '--timeout', '120'
        ])

        # Run security tests
        benchmark = AutomatedBenchmark(
            model='claude-code',
            output_dir='output/claude-code',
            report_name=f"claude-code_208point_{datetime.now().strftime('%Y%m%d')}",
            ...
        )
        summary = benchmark.run_benchmark()
        all_results['claude-code'] = (summary, len(files))
```

---

## Testing

### Quick Test (Verified)
```bash
python3 auto_benchmark.py --all --limit 1
```

**Output:**
```
FULL BENCHMARK: 26 models
======================================================================
API models (parallel):      14
Ollama models (sequential): 9
Cursor models:              1
Codex.app models:           1
Claude Code models:         1
Started: 2026-03-21 02:19:23
```

✅ Successfully recognizes all 26 models across 6 provider types!

### Full Run (Not tested - would take hours)
```bash
python3 auto_benchmark.py --all --retries 3
```

This will:
1. Generate code for all 66 prompts using all 26 models
2. Run 208-point security tests on each
3. Generate JSON and HTML reports
4. Rank all models by security score

---

## Integration Benefits

### Before Integration
- Manual execution required for each tool:
  ```bash
  python3 scripts/test_codex_app.py
  python3 runner.py --code-dir output/codex-app --model codex-app

  python3 scripts/test_claude_code.py
  python3 runner.py --code-dir output/claude-code --model claude-code
  ```

### After Integration
- Single command runs everything:
  ```bash
  python3 auto_benchmark.py --all --retries 3
  ```

- Consistent handling across all tools
- Automatic error handling and logging
- Parallel execution where possible
- Final comparison table with rankings

---

## Model Provider Detection

The `_detect_provider()` function now recognizes:

1. **codex-app** - Desktop application wrappers
2. **claude-code** - CLI wrappers
3. **cursor** - IDE-based tools
4. **openai** - OpenAI API models (gpt-*, o1, o3, o4)
5. **anthropic** - Anthropic API models (claude-*)
6. **google** - Google API models (gemini-*)
7. **ollama** - Local models via Ollama

This enables proper categorization in results tables and provider-specific handling.

---

## Results Integration

Both new tools are integrated into the final results table:

```
Rank  Model                         Score              Files     Provider
--------------------------------------------------------------------------------
1     codex-app                     191/208 (91.8%)    66/66    codex-app
2     starcoder2                    184/208 (88.5%)    66/66    ollama
3     gpt-5.2                       153/208 (73.6%)    66/66    openai
4     cursor                        138/208 (66.3%)    66/66    cursor
5     claude-opus-4-6               137/208 (65.9%)    66/66    anthropic
6     claude-code                   TBD                TBD      claude-code
...
```

---

## Files Modified

1. **benchmark_config.yaml**
   - Added `codex-app` section (lines 48-51)
   - Added `claude-code` section (lines 53-56)

2. **auto_benchmark.py**
   - Updated `_detect_provider()` (lines 182-197)
   - Updated `load_models_from_config()` (lines 194-208)
   - Updated `run_all_models()`:
     - Variable initialization (lines 219-222, 230-231)
     - Phase 4: Codex.app (lines 346-396)
     - Phase 5: Claude Code (lines 398-444)
     - Phase numbering updated (line 448)

---

## Next Steps

### When Claude Code Benchmark Completes

Currently running in background (PID 5885, started 2:16 AM):
```bash
# Check progress
ls -1 output/claude-code/*.{py,js} 2>/dev/null | wc -l

# Check if still running
ps aux | grep test_claude_code | grep -v grep

# View log
tail -f claude_code_full.log
```

**When complete:**
1. Results will be available at `output/claude-code/`
2. Can run full auto_benchmark with all 3 wrappers:
   ```bash
   python3 auto_benchmark.py --all --retries 3
   ```
3. Will generate comprehensive comparison across:
   - 11 OpenAI API models
   - 2 Anthropic API models
   - 1 Google model
   - 9 Ollama models
   - **3 wrapper tools** (Cursor, Codex.app, Claude Code)

---

## Research Value

This integration enables answering:

1. **Wrapper Engineering Effectiveness**
   - Does application-level security engineering work?
   - Codex.app improved GPT-5.4 by +27% → validates approach
   - Will Claude Code improve Claude API similarly?

2. **Vendor Comparison**
   - OpenAI vs Anthropic wrapper strategies
   - Which company prioritizes security more?

3. **Tool Recommendations**
   - Best tools for secure code generation
   - When to use wrappers vs raw APIs

4. **Consistency Analysis**
   - Do security patterns transfer across tools?
   - Are improvements consistent or tool-specific?

---

## Status

✅ **Integration Complete**
🏃 **Claude Code benchmark running** (8/66 files, started 2:16 AM)
📊 **Codex.app results available** (191/208, 91.8%, rank #1)
🔜 **Ready for full comparison** when Claude Code completes

---

**Command to run full benchmark:**
```bash
python3 auto_benchmark.py --all --retries 3
```

**Estimated time:**
- API models (parallel): ~15-20 min
- Ollama models (sequential): ~60-90 min
- Wrappers (Cursor, Codex, Claude Code): ~60 min each
- **Total: ~3-4 hours** for all 26 models

---

*Generated: March 21, 2026, 2:20 AM*
