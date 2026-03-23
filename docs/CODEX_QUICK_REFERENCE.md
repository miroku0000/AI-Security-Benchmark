# Codex Quick Reference

**One-page reference for Codex.app and API usage**

---

## Installation

```bash
# Download from: https://openai.com/codex
# Install Codex.app to /Applications/

# Add CLI to PATH
export PATH="/Applications/Codex.app/Contents/Resources:$PATH"

# Verify
codex --version
```

---

## Authentication

```bash
# Sign in
codex login

# Or use GUI
open -a Codex
```

---

## Basic Usage

```bash
# Generate code (interactive)
codex "Write a Python function to sort a list"

# Non-interactive
codex exec "Write hello world in Python"

# Specify model
codex exec "Write code" -m gpt-5.4
codex exec "Write code" -m o3

# Code review
codex exec review
```

---

## Benchmark Usage

```bash
# Check installation
python3 scripts/test_codex_app.py --check

# Test 3 prompts (~2 minutes)
python3 scripts/test_codex_app.py --limit 3

# Full benchmark (~35 minutes)
python3 scripts/test_codex_app.py

# Security tests
python3 runner.py --code-dir output/codex-app --model codex-app

# View results
cat reports/codex-app_208point_*.json
```

---

## API Alternative

```bash
# Use OpenAI API instead of Codex.app
export OPENAI_API_KEY='sk-...'

# GPT-4o (modern Codex)
python3 scripts/test_codex.py --model gpt-4o

# GPT-5.4 (same as Codex.app default)
python3 scripts/test_codex.py --model gpt-5.4

# Auto-detect best model
python3 scripts/test_codex.py
```

---

## Comparison

| Tool | Installation | Model | Score | Rank |
|------|--------------|-------|-------|------|
| **Codex.app** | Download app | GPT-5.4 | Testing... | ? |
| **GPT-5.4 API** | pip install | GPT-5.4 | 134/208 (64.4%) | #8 |
| **GPT-4o API** | pip install | GPT-4o | 95/208 (45.7%) | #21 |
| **Cursor Agent** | curl install | Auto | 138/208 (66.3%) | #5 |

---

## Troubleshooting

```bash
# Not found?
ls /Applications/Codex.app  # Should exist

# Auth issues?
codex logout && codex login

# CLI not in PATH?
/Applications/Codex.app/Contents/Resources/codex --version

# Test manually
codex exec "print('hello')"
```

---

## Files

- **Installation Guide**: `CODEX_APP_INSTALLATION.md`
- **Benchmark Script**: `scripts/test_codex_app.py`
- **API Script**: `scripts/test_codex.py`
- **Running Status**: `CODEX_APP_RUNNING.md`
- **Results Summary**: `CODEX_BENCHMARK_SUMMARY.md`

---

**Quick Links**:
- Download: https://openai.com/codex
- Docs: https://platform.openai.com/docs
- Support: https://community.openai.com
