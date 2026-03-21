# Codex/OpenAI Code Generation Automation Guide

**Date**: March 21, 2026
**Status**: Ready for Production

---

## Overview

This guide shows how to automatically generate code for all security benchmark prompts using OpenAI's code generation models (GPT-4o, GPT-4, etc.) and test their security.

**Note**: GPT-4o is OpenAI's modern replacement for the deprecated Codex models. When we refer to "Codex" in this benchmark, we mean GPT-4o and its variants.

### Available Models

The script auto-detects the best available OpenAI code model. As of March 2026:

**Currently Working:**
- `gpt-4o` - Best quality, modern Codex replacement ✅ **Recommended** (Rank #21, 45.7%)
- `gpt-4o-mini` - Faster, more efficient version (Rank #20, 47.6%)
- `gpt-3.5-turbo` - Fallback option (Rank #25, 44.2%)

**Listed but Not Yet Available:**
- `gpt-5.3-codex` - Returns server errors (likely in beta)
- `gpt-5.2-codex` - Model not supported yet
- `gpt-5.1-codex-max` - Model not supported yet
- `gpt-5.1-codex` - Model not supported yet
- `gpt-5-codex` - Only available to select users

**Legacy (Deprecated):**
- `code-davinci-002` - Original Codex (deprecated March 2023)
- `code-cushman-001` - Original Codex (deprecated March 2023)

---

## Quick Start

### 1. Setup

Ensure you have the OpenAI API key set:

```bash
export OPENAI_API_KEY='your-api-key-here'
```

### 2. Check Available Models

```bash
python3 scripts/test_codex.py --check-models
```

Expected output:
```
Checking available OpenAI models...

Found 6 code-related models:
  - gpt-5-codex
  - gpt-5.1-codex
  - gpt-5.1-codex-max
  - gpt-5.1-codex-mini
  - gpt-5.2-codex
  - gpt-5.3-codex

✓ Will use: gpt-4o
```

### 3. Test with a Few Prompts

```bash
# Test with first 3 prompts
python3 scripts/test_codex.py --limit 3
```

### 4. Run Full Benchmark

```bash
# Generate code for all 66 prompts
python3 scripts/test_codex.py

# Or use specific model
python3 scripts/test_codex.py --model gpt-4o

# Or run in background
nohup python3 scripts/test_codex.py > codex_benchmark.log 2>&1 &
```

### 5. Run Security Tests

```bash
# Test generated code for vulnerabilities
python3 runner.py --code-dir output/codex --model gpt-4o
```

### 6. View Results

```bash
# View JSON report
cat reports/gpt-4o_208point_*.json

# View HTML report
open reports/gpt-4o_208point_*.html
```

---

## Command Reference

### Full Options

```bash
python3 scripts/test_codex.py \
  --prompts prompts/prompts.yaml \        # Prompts file
  --output-dir output/gpt-4o \            # Output directory
  --model gpt-4o \                        # Specific model
  --timeout 60 \                          # Timeout per prompt (seconds)
  --limit 10 \                            # Test first 10 prompts only
  --check-models                          # Just check available models
```

### Common Use Cases

**Generate code with specific model:**
```bash
python3 scripts/test_codex.py --model gpt-4o-mini --output-dir output/gpt-4o-mini
```

**Test a subset:**
```bash
python3 scripts/test_codex.py --limit 5 --output-dir output/test
```

**Run full benchmark in background:**
```bash
nohup python3 scripts/test_codex.py --model gpt-4o > gpt4o_benchmark.log 2>&1 &

# Monitor progress
tail -f gpt4o_benchmark.log

# Or check file count
ls -1 output/codex/*.py output/codex/*.js 2>/dev/null | wc -l
```

---

## Expected Performance

### GPT-4o Estimates

- **Total prompts**: 66
- **Expected time**: 4-6 minutes (avg 4-5s per prompt)
- **Success rate**: ~98-100%
- **Output size**: ~50-100 KB total

### Cost Estimates (March 2026 Pricing)

**GPT-4o:**
- Input: ~66 prompts × 200 tokens = 13,200 tokens × $0.005/1K = $0.07
- Output: ~66 files × 500 tokens = 33,000 tokens × $0.015/1K = $0.50
- **Total: ~$0.57 per full benchmark run**

**GPT-4o-mini:**
- Input: $0.15/1M tokens → $0.002
- Output: $0.60/1M tokens → $0.020
- **Total: ~$0.022 per full benchmark run** (96% cheaper)

---

## Monitoring Progress

### Check Running Process

```bash
# Find process
ps aux | grep test_codex

# Monitor log
tail -f codex_benchmark.log

# Count generated files
watch -n 5 'ls -1 output/codex/*.{py,js} 2>/dev/null | wc -l'
```

### Expected Progress

```
[1/66] sql_001 (sql_injection, python)...
  ✅ Saved to output/codex/sql_001.py (1069 bytes)
[2/66] sql_002 (sql_injection, javascript)...
  ✅ Saved to output/codex/sql_002.js (902 bytes)
...
```

---

## Troubleshooting

### Error: No API Key

```
ERROR: OPENAI_API_KEY environment variable not set
```

**Fix:**
```bash
export OPENAI_API_KEY='sk-...'
```

### Error: Model Not Supported

```
Error code: 404 - This model is not supported
```

**Fix:** Use `--model gpt-4o` explicitly:
```bash
python3 scripts/test_codex.py --model gpt-4o
```

### Error: Rate Limit

```
Error code: 429 - Rate limit exceeded
```

**Fix:** The script includes 1-second delays between requests. If you still hit limits:
- Wait a few minutes and retry
- Use a lower-tier model (gpt-3.5-turbo)
- Increase sleep time in `test_codex.py` line 275

### Error: Server Error 500

```
Error code: 500 - The server had an error
```

**Cause:** Model is listed but not yet available (e.g., gpt-5.3-codex)

**Fix:** Use `--model gpt-4o` instead

---

## Output Structure

### Generated Files

```
output/codex/
├── sql_001.py              # Generated Python code
├── sql_002.js              # Generated JavaScript code
├── sql_003.py
├── xss_001.js
├── ...
└── gpt-4o_generation_results.json  # Metadata
```

### Results After Security Testing

```
reports/
├── gpt-4o_208point_20260321.json   # Detailed JSON report
└── gpt-4o_208point_20260321.html   # Visual HTML report
```

---

## Comparing Models

To compare multiple OpenAI models:

```bash
# GPT-4o
python3 scripts/test_codex.py --model gpt-4o --output-dir output/gpt-4o
python3 runner.py --code-dir output/gpt-4o --model gpt-4o

# GPT-4o-mini
python3 scripts/test_codex.py --model gpt-4o-mini --output-dir output/gpt-4o-mini
python3 runner.py --code-dir output/gpt-4o-mini --model gpt-4o-mini

# GPT-3.5
python3 scripts/test_codex.py --model gpt-3.5-turbo --output-dir output/gpt-3.5-turbo
python3 runner.py --code-dir output/gpt-3.5-turbo --model gpt-3.5-turbo

# Compare results
ls -lh reports/*_208point_*.json
```

---

## Integration with Benchmark

### Full Workflow

1. **Generate code:**
   ```bash
   python3 scripts/test_codex.py --model gpt-4o
   ```

2. **Test security:**
   ```bash
   python3 runner.py --code-dir output/codex --model gpt-4o
   ```

3. **View results:**
   ```bash
   open reports/gpt-4o_208point_*.html
   ```

4. **Update rankings:**
   - Results automatically include score (e.g., 142/208 = 68.3%)
   - Add to WHITEPAPER.md model comparison table
   - Update README.md with new model entry

---

## API Rate Limits

**GPT-4o (Tier 4):**
- 800,000 tokens/minute
- 10,000 requests/minute
- **Benchmark uses: ~46K tokens, 66 requests = well within limits**

**GPT-4o-mini (Tier 4):**
- 2,000,000 tokens/minute
- 10,000 requests/minute

**With 1-second delays:**
- 66 requests × 1 second = 66 seconds minimum
- Actual time: ~4-6 minutes total

---

## Future: GPT-5 Codex

When GPT-5 Codex models become available:

1. Check availability:
   ```bash
   python3 scripts/test_codex.py --check-models
   ```

2. Test with small batch:
   ```bash
   python3 scripts/test_codex.py --model gpt-5.3-codex --limit 5
   ```

3. If successful, run full benchmark:
   ```bash
   python3 scripts/test_codex.py --model gpt-5.3-codex --output-dir output/gpt-5.3-codex
   ```

The script is already configured to support these models once they're released.

---

## Advanced Usage

### Custom Temperature

Edit `scripts/test_codex.py` line 96 to change temperature:

```python
temperature=0.2,  # Change to 0.0 (deterministic) or 0.7 (creative)
```

### Custom Prompting

Edit `scripts/test_codex.py` lines 90 or 106 to modify prompt strategy:

```python
enhanced_prompt = f"{prompt}\n\nYour custom instruction here."
```

### Batch Processing

```bash
# Generate for multiple models in parallel
for model in gpt-4o gpt-4o-mini gpt-3.5-turbo; do
  python3 scripts/test_codex.py --model $model --output-dir output/$model &
done
wait

# Test all
for model in gpt-4o gpt-4o-mini gpt-3.5-turbo; do
  python3 runner.py --code-dir output/$model --model $model
done
```

---

## Comparison: Codex vs Cursor

| Feature | Codex (GPT-4o) | Cursor Agent CLI |
|---------|----------------|------------------|
| **API Type** | REST API | CLI tool |
| **Cost** | $0.57/run | Free (Pro: $20/month unlimited) |
| **Speed** | 4-6 min | 19 min |
| **Completion** | 98-100% | 100% |
| **Integration** | Script-based | Command-line |
| **Availability** | API key needed | Cursor account needed |

**Use Codex when:**
- You want API-based automation
- You need multiple model comparisons
- You want faster generation

**Use Cursor when:**
- You want IDE integration
- You prefer CLI tools
- You have Cursor Pro subscription

---

## Files

- **Generation Script**: `scripts/test_codex.py`
- **Generated Code**: `output/codex/` or `output/gpt-4o/`
- **Results**: `reports/gpt-4o_208point_*.json`
- **This Guide**: `CODEX_AUTOMATION_GUIDE.md`

---

## Next Steps

1. ✅ Run `--check-models` to verify API access
2. ✅ Test with `--limit 3` to validate setup
3. ✅ Run full benchmark with `gpt-4o`
4. ✅ Analyze security results
5. ✅ Compare with Cursor/Claude results
6. ✅ Update whitepaper with findings

---

**Last Updated**: March 21, 2026
**Status**: Production Ready
**Tested Models**: gpt-4o ✅, gpt-4o-mini ✅, gpt-3.5-turbo ✅
