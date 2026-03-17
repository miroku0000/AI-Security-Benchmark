# Ollama Quick Start - 5 Minutes to Testing

Get started testing AI code security with Ollama in 5 minutes.

## Step 1: Install & Setup (2 minutes)

```bash
# Install Ollama (macOS)
brew install ollama

# Or download from https://ollama.ai

# Pull CodeLlama model
ollama pull codellama

# Note: Ollama will auto-start when you run tests!
# No need to manually run "ollama serve"
```

## Step 2: Run Quick Test (2 minutes)

```bash
# Interactive test (recommended for first time)
./quick_test.sh

# Or run directly
python3 auto_benchmark.py --model codellama --limit 5
```

## Step 3: View Results (1 minute)

Results appear in console and are saved to:
- `reports/codellama_*.json` - Data
- `reports/codellama_*.html` - Visual report

Open the HTML report:
```bash
open reports/codellama_*.html
```

Example console output:
```
======================================================================
FINAL RESULTS
======================================================================
Model: codellama
Total Tests: 5
✅ Secure: 2
⚠️  Partial: 1
❌ Vulnerable: 2

Overall Score: 5/10 (50.0%)
======================================================================
```

## What Just Happened?

1. **Generated** code for 5 security-critical scenarios using CodeLlama
2. **Tested** the generated code for common vulnerabilities
3. **Scored** each sample (0=vulnerable, 1=partial, 2=secure)
4. **Reported** results in console and JSON

## Next Steps

### Run Full Benchmark (38 prompts)

```bash
python3 auto_benchmark.py --model codellama
```

Takes ~30-60 minutes depending on your hardware.

### Compare Multiple Models

```bash
# Test multiple models automatically
./batch_compare.sh codellama deepseek-coder

# Or manually:
python3 auto_benchmark.py --model codellama
python3 auto_benchmark.py --model deepseek-coder
python3 compare_results.py reports/codellama_*.json reports/deepseek-coder_*.json
```

### Try Different Models

```bash
# Pull and test other models
ollama pull deepseek-coder
python3 auto_benchmark.py --model deepseek-coder --limit 5

ollama pull qwen2.5-coder
python3 auto_benchmark.py --model qwen2.5-coder --limit 5
```

## Common Issues

**"Ollama is not running"**
```bash
# Check if running
ollama list

# Start if needed (usually automatic on macOS)
ollama serve
```

**"Model not found"**
```bash
# Pull the model first
ollama pull codellama
```

**Too slow?**
- Use `--limit 5` for quick tests
- Try smaller models (7B instead of 13B)
- Run overnight for full 38-prompt benchmark

## Understanding Results

- **✅ SECURE (2/2)**: Code implements proper security controls
- **⚠️ PARTIAL (1/2)**: Some protections but incomplete
- **❌ VULNERABLE (0/2)**: Contains exploitable security flaws

Common vulnerabilities detected:
- SQL injection (string concatenation in queries)
- XSS (innerHTML with user input)
- Command injection (os.system with user input)
- Hardcoded secrets
- Path traversal
- And more...

## Files Generated

```
generated_codellama/           # Generated code samples
├── sql_001.py                # SQL injection test
├── xss_001.js                # XSS test
├── cmd_001.py                # Command injection test
└── ...

reports/                       # Test results
└── codellama_20260109_*.json # Detailed results
```

## Pro Tips

1. **Start small**: Use `--limit 5` first to verify setup
2. **Test overnight**: Full 38 prompts can take time
3. **Compare models**: See which AI generates more secure code
4. **Check reports**: JSON files have detailed vulnerability info

## Full Documentation

- [OLLAMA_GUIDE.md](OLLAMA_GUIDE.md) - Complete Ollama guide
- [README.md](README.md) - Project overview
- [USAGE.md](USAGE.md) - Detailed usage instructions

## Example Complete Workflow

```bash
# 1. Quick validation
./quick_test.sh

# 2. Full benchmark (go get coffee)
python3 auto_benchmark.py --model codellama

# 3. Test another model
python3 auto_benchmark.py --model deepseek-coder

# 4. Compare
python3 compare_results.py \
    reports/codellama_*.json \
    reports/deepseek-coder_*.json \
    "CodeLlama" \
    "DeepSeek"

# 5. Review JSON reports for details
cat reports/codellama_*.json | jq '.summary'
```

That's it! You're now benchmarking AI code security. 🎉
