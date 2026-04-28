# GitHub Copilot Auto-Benchmark Integration

## Overview

GitHub Copilot CLI has been fully integrated into the automated benchmark system (`auto_benchmark.py`). This allows GitHub Copilot to be tested alongside all other AI models in a single command.

## What Was Done

### 1. Restored `benchmark_config.yaml`

The `benchmark_config.yaml` file was accidentally deleted in commit `1697f01f4`. It has been restored with all original models plus GitHub Copilot:

```yaml
models:
  openai: [...]
  anthropic: [...]
  google: [...]
  ollama: [...]
  cursor: [cursor]
  codex-app: [codex-app]
  claude-code: [claude-code]
  github-copilot: [github-copilot]  # NEW
```

### 2. Updated `auto_benchmark.py`

**Added GitHub Copilot support:**

- **Provider detection** (`_detect_provider`): Detects `github-copilot` model names
- **Config loader** (`load_models_from_config`): Loads `github-copilot` models from config
- **Phase 6**: Added GitHub Copilot generation and testing phase
- **Phase 7**: Shifted HTML report generation (was Phase 6)

**Integration pattern:**

```python
# Check if copilot CLI is available
has_copilot = bool(shutil.which('copilot'))

if has_copilot:
    # Run code generation
    subprocess.run(['python3', 'scripts/test_github_copilot.py', ...])

    # Run security tests
    benchmark = AutomatedBenchmark(model='github-copilot', ...)
    summary = benchmark.run_benchmark()

    # Collect results
    all_results['github-copilot'] = (summary, files)
```

### 3. Integration with Existing Scripts

The system now uses the following scripts in sequence:

1. **scripts/test_github_copilot.py** - Generates code using `copilot -p "<prompt>" -s`
2. **runner.py** - Runs security tests on generated code
3. **utils/generate_html_reports.py** - Creates HTML reports (Phase 7)

## Usage

### Run Full Benchmark with GitHub Copilot

```bash
# Run ALL models including GitHub Copilot
python3 auto_benchmark.py --all

# Quick test (5 prompts only)
python3 auto_benchmark.py --all --limit 5
```

### Prerequisites

1. **Install GitHub Copilot CLI:**
   ```bash
   npm install -g @githubnext/github-copilot-cli
   ```

2. **Authenticate:**
   ```bash
   copilot auth login
   ```

3. **Verify installation:**
   ```bash
   copilot --version
   ```

### What Happens

When you run `python3 auto_benchmark.py --all`, the system:

1. **Phase 1**: Runs API models (OpenAI, Anthropic, Google) in parallel
2. **Phase 2**: Runs Ollama models sequentially
3. **Phase 3**: Runs Cursor (if available)
4. **Phase 4**: Runs Codex.app (if available)
5. **Phase 5**: Runs Claude Code CLI (if available)
6. **Phase 6**: Runs GitHub Copilot CLI (if available) ← **NEW**
7. **Phase 7**: Generates HTML reports

### Expected Output

```
======================================================================
FULL BENCHMARK: 28 models
======================================================================
API models (parallel):      13
Ollama models (sequential): 9
Cursor models:              1
Codex.app models:           1
Claude Code models:         1
GitHub Copilot models:      1
Started: 2026-04-22 10:30:00
======================================================================

...

======================================================================
PHASE 6: GITHUB COPILOT MODELS (1 models)
======================================================================
>>> Running GitHub Copilot benchmark...

================================================================================
GITHUB COPILOT CLI BENCHMARK TEST
================================================================================
Prompts file: prompts/prompts.yaml
Output dir:   output/github-copilot
Total prompts: 730
Timeout:      120s per prompt
================================================================================

[1/730] sql_001 (sql_injection, python)...
  ✅ Saved to output/github-copilot/sql_001.py

[2/730] sql_002 (sql_injection, javascript)...
  ✅ Saved to output/github-copilot/sql_002.js

...

>>> Running security tests on GitHub Copilot output...

======================================================================
STEP 2: SECURITY TESTING
======================================================================
Running tests on 730 files...
✅ 1628 tests passed
Report: reports/github-copilot_208point_20260422.json

======================================================================
PHASE 7: GENERATING HTML REPORTS
======================================================================
...

======================================================================
FINAL RESULTS -- ALL MODELS
======================================================================
Rank  Model                         Score              Files     Provider
----------------------------------------------------------------------------
1     codex-app-security-skill      1365/1628 (83.8%)  730/730   codex-app
2     codex-app                     1281/1628 (78.7%)  730/730   codex-app
3     claude-code                   1025/1616 (63.4%)  728/730   claude-code
4     github-copilot                TBD                730/730   github-copilot
...
======================================================================
```

## File Structure

After running the benchmark, you'll have:

```
output/github-copilot/
├── sql_001.py
├── sql_002.js
├── xss_001.py
├── ... (730 files)
└── github_copilot_generation_results.json

reports/
├── github-copilot_208point_20260422.json
└── github-copilot_208point_20260422.html
```

## Configuration

### Adding GitHub Copilot to Custom Config

If you have a custom `benchmark_config.yaml`:

```yaml
models:
  # ... other providers ...

  github-copilot:
    - github-copilot
```

### Skipping GitHub Copilot

If you don't want to test GitHub Copilot, simply remove it from `benchmark_config.yaml` or don't install the CLI.

## How It Works

### Code Generation Flow

1. **auto_benchmark.py** checks if `copilot` command exists using `shutil.which()`
2. If found, runs **scripts/test_github_copilot.py**
3. **test_github_copilot.py** loops through all 730 prompts:
   - Calls `copilot -p "<prompt>" -s` for each prompt
   - Extracts code from output (handles markdown, explanations)
   - Saves to `output/github-copilot/<id>.<ext>`
4. **auto_benchmark.py** then runs **runner.py** for security testing
5. Results are collected and included in final summary

### Security Testing Flow

1. **runner.py** loads all files from `output/github-copilot/`
2. Runs 35+ security detectors on each file
3. Scores each test: 0 (vulnerable), 1 (partial), 2 (secure)
4. Generates JSON report with detailed findings
5. Generates HTML report for easy viewing

## Troubleshooting

### Issue: GitHub Copilot CLI not found

**Symptom:**
```
WARNING  GitHub Copilot CLI not found - skipping GitHub Copilot models
WARNING  Install GitHub Copilot CLI: npm install -g @githubnext/github-copilot-cli
```

**Solution:**
```bash
# Install via npm
npm install -g @githubnext/github-copilot-cli

# Authenticate
copilot auth login

# Verify
copilot --version
```

### Issue: `copilot` command not in PATH

**Solution:**
```bash
# Add to PATH (macOS/Linux)
source ~/.zshrc  # or ~/.bashrc

# Verify
which copilot
```

### Issue: Timeout errors during generation

Many prompts may timeout with default 120s setting.

**Solution:**

Edit `auto_benchmark.py` line 480:
```python
# Change from:
'--timeout', '120'

# To:
'--timeout', '180'  # or higher
```

Or run manually with higher timeout:
```bash
python3 scripts/test_github_copilot.py --timeout 180
python3 runner.py --code-dir output/github-copilot --model github-copilot
```

### Issue: Rate limiting

GitHub may rate limit excessive requests during full benchmark.

**Solution:**

Run in smaller batches:
```bash
# Generate code first (may take 24+ hours)
python3 scripts/test_github_copilot.py --limit 100

# Then continue from where it left off (script auto-skips existing files)
python3 scripts/test_github_copilot.py

# Run security tests when done
python3 runner.py --code-dir output/github-copilot --model github-copilot
```

## Comparison with Other CLI Tools

| Tool | Command | Integration Phase | Output Directory |
|------|---------|-------------------|------------------|
| Cursor | `agent` | Phase 3 | `output/cursor` |
| Codex.app | `codex` | Phase 4 | `output/codex-app` |
| Claude Code | `claude` | Phase 5 | `output/claude-code` |
| **GitHub Copilot** | **`copilot`** | **Phase 6** | **`output/github-copilot`** |

All CLI tools follow the same integration pattern:
1. Check if CLI command exists
2. Run generation script (scripts/test_*.py)
3. Run security tests (runner.py)
4. Collect results for final summary

## Next Steps

1. **Run full benchmark:**
   ```bash
   python3 auto_benchmark.py --all
   ```

2. **View results:**
   ```bash
   cat reports/github-copilot_208point_*.json | jq '.summary'
   open reports/html/index.html
   ```

3. **Compare against other models:**
   ```bash
   cat reports/model_security_rankings.csv
   ```

## Related Documentation

- **docs/GITHUB_COPILOT_INTEGRATION.md** - GitHub Copilot CLI setup and usage guide
- **scripts/test_github_copilot.py** - Code generation script
- **README.md** - Main benchmark documentation
- **docs/PIPELINE_GUIDE.md** - End-to-end workflow guide

## Technical Details

### Modified Files

1. **benchmark_config.yaml** (restored + updated)
   - Added `github-copilot: [github-copilot]`

2. **auto_benchmark.py** (4 changes)
   - `_detect_provider()`: Added GitHub Copilot detection
   - `load_models_from_config()`: Added `github-copilot` to return dict
   - `run_all_models()`: Added Phase 6 for GitHub Copilot
   - Updated total count and logging

3. **scripts/test_github_copilot.py** (already created)
   - Handles code generation using `copilot -p <prompt> -s`
   - Intelligent code extraction (markdown blocks, pattern matching)
   - Resumable (skips existing files)
   - Progress tracking and JSON results

4. **docs/GITHUB_COPILOT_INTEGRATION.md** (already created)
   - Installation and setup guide
   - Usage examples and troubleshooting
   - Expected results and comparison metrics

---

**Status:** ✅ Complete
**Branch:** featureGithubCopilot
**Last Updated:** April 22, 2026
**Integration Ready:** Yes - ready for `python3 auto_benchmark.py --all`
