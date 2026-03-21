# Quick Start: Codex/OpenAI Automation

**Ready to use!** ✅

## To test Codex security right now:

### Option 1: Quick Test (3 prompts, 30 seconds)
```bash
python3 scripts/test_codex.py --limit 3
```

### Option 2: Full Benchmark (66 prompts, ~5 minutes)
```bash
# Generate all code
python3 scripts/test_codex.py --model gpt-4o

# Test security
python3 runner.py --code-dir output/codex --model gpt-4o

# View results
open reports/gpt-4o_208point_*.html
```

### Option 3: Background Run
```bash
nohup python3 scripts/test_codex.py --model gpt-4o > codex.log 2>&1 &

# Monitor
tail -f codex.log

# Or check progress
ls -1 output/codex/*.{py,js} 2>/dev/null | wc -l  # Should reach 66
```

## What You'll Get

- **Generated Code**: `output/codex/` with 66 files (Python, JS, Java, Go, Rust)
- **Security Report**: `reports/gpt-4o_208point_YYYYMMDD.json`
- **HTML Report**: `reports/gpt-4o_208point_YYYYMMDD.html`
- **Score**: e.g., "138/208 (66.3%)" to compare with Cursor, Claude, etc.

## Available Models

- **gpt-4o** ⭐ Recommended (best quality, $0.57/run)
- **gpt-4o-mini** 💰 Cost-effective ($0.02/run, 96% cheaper)
- **gpt-3.5-turbo** 🔄 Fallback option

## Requirements

- OpenAI API key: `export OPENAI_API_KEY='sk-...'`
- Python 3.11+ with `openai` package (already installed)

## For More Details

See `CODEX_AUTOMATION_GUIDE.md` for full documentation.

---

**That's it!** Run the command and watch it generate and test all 66 security prompts automatically.
