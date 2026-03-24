# Cursor Agent CLI Integration Guide

## Overview

Cursor Agent is an AI-powered CLI tool for automated code generation. This benchmark integrates the Cursor Agent CLI to test its code security alongside other AI models.

**Note**: This uses the **Cursor Agent CLI** (`agent` command), not the Cursor IDE. They are separate tools.

## Installation

### Install Cursor Agent CLI

```bash
# Install the Cursor Agent CLI
curl https://cursor.com/install -fsSL | bash

# Add to PATH (installer does this automatically, but verify)
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc

# Verify installation
agent --version
# Should output: 2026.03.20-44cb435 (or similar)
```

**Installation Location**: `~/.local/bin/agent`

**Free Plan Note**: Free plans can only use the "Auto" model. Named models (GPT-5, Claude Sonnet, etc.) require a Cursor Pro subscription.

## Running Cursor Benchmark

### Standalone Testing

Test Cursor Agent independently:

```bash
# Quick test (5 prompts) - recommended timeout 180s for complex prompts
python3 scripts/test_cursor.py --limit 5 --timeout 180

# Full benchmark (all 66 prompts) - takes ~3-5 hours
python3 scripts/test_cursor.py --timeout 180

# Run in background
nohup python3 scripts/test_cursor.py --timeout 180 > cursor_test.log 2>&1 &
tail -f cursor_test.log
```

**Timeout Recommendations**:
- Simple prompts: 30-60s
- Benchmark prompts (complex): 180-300s
- Default in script: 60s (may timeout on complex prompts)

### Integrated Testing

Cursor Agent is automatically included when you run the full benchmark:

```bash
# Run all models including Cursor Agent
python3 auto_benchmark.py --all

# Cursor will be tested automatically if agent command is found
# If not found, benchmark will skip it with a warning
```

### Direct Command Line Usage

You can also use the agent directly:

```bash
# Simple test
agent --print --output-format text --trust --model auto "Write a Python hello world"

# With JSON output
agent --print --output-format json --trust --model auto "Write a function to add numbers"
```

## How It Works

1. **Code Generation**: `scripts/test_cursor.py` uses `agent --print --model auto` to generate code for each prompt
2. **Code Extraction**: The script parses Cursor's markdown output and extracts code blocks
3. **File Saving**: Code is saved to `output/cursor/` with appropriate file extensions
4. **Security Testing**: Standard `runner.py` tests are run on the generated code
5. **Reports**: Results appear in `reports/cursor_208point_*.json` and HTML reports

**Command Used**:
```bash
agent --print --output-format text --trust --model auto "<prompt>"
```

## Features

- ✅ **Headless Mode**: Runs without opening Cursor UI
- ✅ **Automatic Code Extraction**: Parses markdown code blocks from Cursor output
- ✅ **Multiple Languages**: Supports Python, JavaScript, TypeScript, Java, Go, Rust, etc.
- ✅ **Timeout Control**: Configurable timeout per prompt
- ✅ **Error Handling**: Gracefully handles failures and reports them
- ✅ **Integration**: Seamlessly integrates with existing benchmark infrastructure

## Configuration

Cursor is configured in `benchmark_config.yaml`:

```yaml
models:
  cursor:
    - cursor
```

## Output Structure

```
output/cursor/
├── sql_001.py
├── sql_002.js
├── xss_001.js
└── ... (66 files total)
```

## Troubleshooting

### agent command not found

```bash
# Check if agent is installed
which agent

# Should show: /Users/yourname/.local/bin/agent

# If not found, reinstall
curl https://cursor.com/install -fsSL | bash

# Add to PATH
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc

# Verify
agent --version
```

### Timeouts with Complex Prompts

The benchmark prompts are complex and may take 2-3 minutes each:

```bash
# Increase timeout to 180 seconds (3 minutes)
python3 scripts/test_cursor.py --limit 5 --timeout 180

# For very complex prompts, use 300 seconds (5 minutes)
python3 scripts/test_cursor.py --timeout 300
```

**Why**: Benchmark prompts include detailed requirements (e.g., "fetch user profiles from PostgreSQL with multiple filter criteria..."). Simple prompts complete in 5-10 seconds.

### Free Plan Model Error

If you see: `Named models unavailable. Free plans can only use Auto.`

**Solution**: The script now uses `--model auto` by default (already fixed).

To use specific models, you need:
- Cursor Pro subscription
- Set API key: `export CURSOR_API_KEY=your-key`
- Specify model: modify script to use `--model gpt-5` or `--model sonnet-4`

### No Code Extracted

If agent outputs explanatory text without code blocks:

1. Check `output/cursor/cursor_generation_results.json` for raw output
2. The extraction logic looks for markdown code blocks: ` ```python ... ``` `
3. Try a simple test: `agent --print --model auto "Write a Python function that adds two numbers"`
4. Verify the output contains code blocks

### Agent Hangs or Takes Too Long

Complex prompts can take several minutes:

```bash
# Test with a simple prompt first
agent --print --output-format text --trust --model auto "Write hello world in Python"

# Should complete in 5-10 seconds
```

If simple prompts hang:
- Check internet connection
- Verify Cursor Agent service is running
- Try reinstalling: `curl https://cursor.com/install -fsSL | bash`

## Comparison with Other Models

Cursor's results will appear in:

1. **HTML Reports**: `reports/html/index.html` - visual comparison
2. **JSON Reports**: `reports/cursor_208point_*.json` - raw data
3. **Summary Table**: Printed when running `python3 auto_benchmark.py --all`

Example output:

```
Rank  Model                        Score             Files      Provider
1     gpt-5.2                      151/208 (72.6%)   66/66      openai
2     starcoder2                   147/208 (70.7%)   66/66      ollama
3     cursor                       140/208 (67.3%)   66/66      cursor
...
```

## Research Applications

Cursor integration enables research on:

1. **IDE-integrated AI vs. API models**: How does Cursor's context-aware generation compare?
2. **Security awareness**: Does Cursor's IDE context help it write more secure code?
3. **Code quality**: Compare generated code style and completeness
4. **User experience**: Cursor is designed for developers - does this affect security?

## Limitations

1. **Context**: CLI mode lacks full IDE context (no open files, no project structure)
2. **Speed**: Cursor Agent is slower than API models (180-300s per prompt vs 5-10s for complex prompts)
3. **Free Plan**: Limited to "Auto" model (no named model selection without Pro subscription)
4. **Determinism**: Without temperature control, results may vary between runs
5. **Timeout Sensitivity**: Complex prompts need generous timeouts (180-300s recommended)

## Performance Benchmarks

| Prompt Type | Estimated Time | Timeout Recommended |
|-------------|----------------|---------------------|
| Simple ("write hello world") | 5-10s | 30s |
| Medium ("write a function with error handling") | 30-60s | 90s |
| Complex (benchmark prompts) | 120-180s | 180-300s |
| Very Complex ("multi-file project") | 180-300s | 300-600s |

**Full Benchmark Time**: 66 prompts × 180s average = ~3-3.5 hours

## Next Steps

```bash
# 1. Verify installation
agent --version

# 2. Quick test with simple prompt
agent --print --model auto "Write Python hello world"

# 3. Test with 1 benchmark prompt (may take 2-3 minutes)
python3 scripts/test_cursor.py --limit 1 --timeout 180

# 4. Run 5 prompts (~15 minutes)
python3 scripts/test_cursor.py --limit 5 --timeout 180

# 5. Full benchmark (run overnight, ~3-5 hours)
nohup python3 scripts/test_cursor.py --timeout 180 > cursor_test.log 2>&1 &

# 6. Integrated benchmark
python3 auto_benchmark.py --all
```

## Support

- **Cursor Agent CLI Docs**: https://cursor.com/docs/cli
- **Cursor Website**: https://cursor.sh
- **Benchmark Issues**: Report at your repository issues
- **Installation Script**: https://cursor.com/install
