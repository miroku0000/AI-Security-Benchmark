# GitHub Copilot CLI Integration

This guide explains how to test GitHub Copilot CLI against the AI Security Benchmark.

## Overview

GitHub Copilot CLI is GitHub's official command-line interface for AI-powered code generation. This benchmark integration allows you to:
- Generate code for all 730 security prompts using Copilot
- Evaluate Copilot's security performance across 35+ programming languages
- Compare Copilot against 27+ other AI models in the benchmark

## Prerequisites

### 1. Install GitHub Copilot CLI

GitHub Copilot CLI is available to GitHub Copilot subscribers.

**Installation:**
```bash
# Install via npm
npm install -g @githubnext/github-copilot-cli

# Or via Homebrew (macOS)
brew install gh
gh extension install github/gh-copilot
```

**Verify installation:**
```bash
copilot --version
```

### 2. Authenticate

```bash
copilot auth login
```

This will open a browser window for GitHub authentication.

### 3. Source Environment

Make sure the `copilot` command is in your PATH:

```bash
source ~/.zshrc  # or ~/.bashrc
which copilot
```

## Usage

### Quick Test (5 prompts)

Test the integration with a small sample:

```bash
python3 scripts/test_github_copilot.py --limit 5
```

**Expected output:**
```
================================================================================
GITHUB COPILOT CLI BENCHMARK TEST
================================================================================
Prompts file: prompts/prompts.yaml
Output dir:   output/github-copilot
Total prompts: 5
Timeout:      120s per prompt
================================================================================

[1/5] sql_001 (sql_injection, python)...
  ✅ Saved to output/github-copilot/sql_001.py

[2/5] sql_002 (sql_injection, javascript)...
  ✅ Saved to output/github-copilot/sql_002.js

...
```

### Full Benchmark (730 prompts)

Run the complete benchmark:

```bash
python3 scripts/test_github_copilot.py
```

**Time estimate:** ~24 hours for 730 prompts at 120s per prompt
- Consider running in batches or using `--limit` for incremental testing
- The script automatically skips already-generated files (resumable)

### Run Security Analysis

After code generation, analyze the security of generated code:

```bash
python3 runner.py --code-dir output/github-copilot --model github-copilot --output reports/github-copilot.json
```

### Generate HTML Report

```bash
python3 utils/generate_html_reports.py
open reports/html/index.html
```

## Command-Line Options

```bash
python3 scripts/test_github_copilot.py --help
```

**Available options:**

| Option | Description | Default |
|--------|-------------|---------|
| `--prompts` | Path to prompts YAML file | `prompts/prompts.yaml` |
| `--output-dir` | Output directory for generated code | `output/github-copilot` |
| `--timeout` | Timeout per prompt (seconds) | `120` |
| `--limit` | Limit number of prompts (for testing) | None (all prompts) |

**Examples:**

```bash
# Test specific category (first 10 SQL prompts)
python3 scripts/test_github_copilot.py --limit 10

# Use custom output directory
python3 scripts/test_github_copilot.py --output-dir output/copilot-test

# Increase timeout for complex prompts
python3 scripts/test_github_copilot.py --timeout 180
```

## How It Works

### 1. Code Generation

The script calls GitHub Copilot CLI for each prompt:

```bash
copilot -p "<prompt text>" -s
```

Flags:
- `-p`: Provide prompt text
- `-s`: Suppress interactive prompts (non-interactive mode)

### 2. Code Extraction

Copilot may include explanations before code. The script uses intelligent extraction:

1. **Try markdown code blocks:**
   - ` ```python ... ``` `
   - ` ``` ... ``` `

2. **Detect code start patterns:**
   - Shebangs: `#!/usr/bin/env python3`
   - Imports: `import os`, `from typing import ...`
   - Function definitions: `def search_users(...)`
   - Class definitions: `class UserRepository:`

3. **Strip explanation text:**
   - "I didn't find an existing DB layer..."
   - "Here's a simple implementation..."

### 3. File Saving

Generated code is saved with appropriate extensions:
- `sql_001.py` (Python)
- `xss_001.js` (JavaScript)
- `docker_001.txt` (Dockerfile)
- etc.

## Expected Results

Based on preliminary testing:

| Metric | Value |
|--------|-------|
| **Completion rate** | ~95-100% |
| **Average time per prompt** | ~60-120s |
| **Code quality** | High (context-aware) |
| **Security posture** | TBD (run full benchmark) |

Copilot typically generates:
- ✅ Clean, idiomatic code
- ✅ Proper imports and structure
- ✅ Functional implementations
- ⚠️ Security varies by prompt category

## Troubleshooting

### Issue: `copilot command not found`

**Solution:**
```bash
# Check installation
which copilot

# Reinstall if needed
npm install -g @githubnext/github-copilot-cli

# Source your shell config
source ~/.zshrc
```

### Issue: Authentication errors

**Solution:**
```bash
# Re-authenticate
copilot auth login

# Check status
copilot auth status
```

### Issue: Timeout errors

Many prompts timeout with default 120s setting.

**Solution:**
```bash
# Increase timeout
python3 scripts/test_github_copilot.py --timeout 180
```

### Issue: Rate limiting

GitHub may rate limit excessive requests.

**Solution:**
- Run in smaller batches using `--limit`
- Add delays between prompts (already implemented: 1s)
- Contact GitHub support for higher limits

### Issue: Explanation text in generated code

The script already handles this, but if you see issues:

**Check:**
```bash
cat output/github-copilot/sql_001.py | head -5
```

If it starts with explanation text (not code), the extraction failed. Please report this as an issue.

## Comparison with Other Models

After running the full benchmark, compare Copilot against other models:

```bash
# View summary CSV
cat reports/model_security_rankings.csv

# View detailed JSON report
cat reports/github-copilot.json | jq '.summary'
```

**Key comparisons:**
- Codex.app with Security Skill: 83.8% (1365/1628)
- Codex.app baseline: 78.7% (1281/1628)
- Claude Code CLI: 63.4% (1025/1616)
- GitHub Copilot CLI: TBD

## Contributing

If you encounter issues with GitHub Copilot integration:

1. Check existing issues: https://github.com/miroku0000/AI-Security-Benchmark/issues
2. Report new issues with:
   - Copilot version (`copilot --version`)
   - Error messages
   - Sample prompts that failed
   - Generated output (if any)

## References

- **GitHub Copilot CLI Docs:** https://docs.github.com/en/copilot/github-copilot-in-the-cli
- **Copilot CLI Repository:** https://github.com/github/gh-copilot
- **AI Security Benchmark:** https://github.com/miroku0000/AI-Security-Benchmark

---

**Last Updated:** April 2026
**Status:** Initial integration complete, full benchmark testing in progress
