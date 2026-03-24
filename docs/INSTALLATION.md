# AI Security Benchmark - Installation Guide

## Prerequisites

- **Python 3.8+** (tested with Python 3.11)
- **Git** (for version control)
- **API Keys** (at least one is required):
  - OpenAI API key (for GPT models)
  - Anthropic API key (for Claude models) - optional
  - Google API key (for Gemini models) - optional
- **Ollama** (optional, for local models like CodeLlama, DeepSeek, etc.)

---

## Quick Start

### 1. Clone the Repository

```bash
git clone <repository-url>
cd AI_Security_Benchmark
```

### 2. Set Up Virtual Environment (Recommended)

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # On macOS/Linux
# OR
venv\Scripts\activate  # On Windows

# Your prompt should now show (venv)
```

### 3. Install Python Dependencies

```bash
pip install -r requirements.txt
```

**Note**: With venv activated, use `pip` instead of `pip3`

This will install:
- `openai` - OpenAI API client (GPT-3.5, GPT-4, GPT-4o, etc.)
- `anthropic` - Anthropic API client (Claude models)
- `google-generativeai` - Google Gemini API client
- `jinja2` - Template rendering for reports
- `pyyaml` - Configuration file parsing
- `Flask`, `Werkzeug`, `PyJWT` - For testing vulnerable code examples
- Optional: `jsonschema`, `markdown`

### 4. Set Up API Keys

#### Option A: Environment Variables (Recommended)

Add to your `~/.bashrc`, `~/.zshrc`, or `~/.bash_profile`:

```bash
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."  # Optional
export GEMINI_API_KEY="..."            # Optional
```

Then reload your shell:
```bash
source ~/.bashrc  # or ~/.zshrc
```

#### Option B: `.env` File

Create a `.env` file in the project directory:

```bash
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GEMINI_API_KEY=...
```

**Note**: Add `.env` to `.gitignore` to avoid committing secrets!

### 5. Install Ollama (Optional)

For local models (CodeLlama, DeepSeek, Llama, Mistral, Qwen, StarCoder):

```bash
# macOS
brew install ollama

# Linux
curl -fsSL https://ollama.com/install.sh | sh

# Start Ollama service
ollama serve
```

Pull models you want to test:
```bash
ollama pull codellama
ollama pull deepseek-coder
ollama pull llama3.1
ollama pull mistral
ollama pull qwen2.5-coder
ollama pull starcoder2
ollama pull codegemma
```

### 6. Verify Installation

Run the environment check script:

```bash
chmod +x scripts/check_environment.sh
./scripts/check_environment.sh
```

This will verify:
- ✅ Python version (>= 3.8)
- ✅ Required Python packages
- ✅ API keys are set
- ✅ Optional tools (Ollama, Git, jq)
- ✅ Ollama models (if Ollama installed)
- ✅ Project structure
- ✅ Write permissions

---

## Running the Benchmark

### Full Benchmark (All Models)

```bash
python3 auto_benchmark.py --all --retries 3
```

**What this does**:
1. Generates code for 141 security prompts using all available models
2. Runs security tests on generated code
3. Creates JSON reports and HTML reports
4. Uses caching to avoid regenerating unchanged code

**Estimated time**: 2-3 hours for first run, 15-30 minutes for re-runs (with caching)

### Single Model

```bash
python3 auto_benchmark.py --model gpt-4o --retries 3
```

### API Models Only

```bash
python3 auto_benchmark.py --api-only --retries 3
```

### Ollama Models Only

```bash
python3 auto_benchmark.py --ollama-only --retries 3
```

---

## Understanding the Output

### Reports Directory

```
reports/
├── gpt-4o_208point_20260321.json      # Raw JSON results
├── gpt-4o_208point_20260321.html      # HTML report with visualizations
├── claude-opus-4-6_208point_20260321.json
└── ...
```

### Output Directory

```
output/
├── gpt-4o/
│   ├── sql_001.py              # Generated code for SQL injection test
│   ├── xss_001.js              # Generated code for XSS test
│   ├── buffer_001.cpp          # Generated code for buffer overflow test
│   └── ...
└── ...
```

### Reading a Report

**JSON Report** (`reports/gpt-4o_*.json`):
```json
{
  "model_name": "gpt-4o",
  "overall_score": 165,
  "overall_max_score": 348,
  "security_percentage": 47.4,
  "detailed_results": [...]
}
```

**HTML Report** (`reports/gpt-4o_*.html`):
- Overall security score
- Category breakdown (SQL injection, XSS, etc.)
- Detailed vulnerability listings
- Code snippets with line numbers
- Security recommendations

---

## Troubleshooting

### "Module not found" errors

```bash
pip3 install -r requirements.txt
```

### "API key not set" warnings

Make sure API keys are exported in your current shell:
```bash
echo $OPENAI_API_KEY  # Should print your key
```

If empty, add to `~/.bashrc` or `~/.zshrc` and reload:
```bash
source ~/.bashrc
```

### Ollama connection errors

Make sure Ollama service is running:
```bash
ollama serve
```

In another terminal:
```bash
ollama list  # Should show installed models
```

### "Permission denied" on scripts

Make scripts executable:
```bash
chmod +x scripts/*.sh
```

### Slow benchmark runs

First run takes 2-3 hours (generates all code). Subsequent runs use caching and take 15-30 minutes.

To force full regeneration:
```bash
python3 auto_benchmark.py --all --force-regenerate --retries 3
```

---

## Advanced Configuration

### Custom Prompts

Edit `prompts.json` to add your own security prompts:

```json
{
  "id": "custom_001",
  "category": "sql_injection",
  "language": "python",
  "prompt": "Your prompt here...",
  "max_score": 8
}
```

### Model Configuration

Edit `auto_benchmark.py` to:
- Add new models
- Change temperature settings
- Modify concurrency limits
- Adjust retry logic

### Detector Configuration

Detectors are in `tests/` directory:
- `test_sql_injection.py` - SQL injection patterns
- `test_xss.py` - XSS patterns
- `test_buffer_overflow.py` - Memory safety
- etc.

Edit patterns to tune detection accuracy.

---

## System Requirements

### Minimum

- **CPU**: 2 cores
- **RAM**: 4 GB
- **Disk**: 2 GB free space
- **Network**: Stable internet for API calls

### Recommended

- **CPU**: 4+ cores (for parallel API calls)
- **RAM**: 8+ GB
- **Disk**: 10 GB free space (for Ollama models)
- **Network**: High-speed internet

### Ollama Models

Each Ollama model requires additional disk space:
- codellama: ~3.8 GB
- deepseek-coder: ~3.7 GB
- llama3.1: ~4.7 GB
- mistral: ~4.1 GB
- qwen2.5-coder: ~7.6 GB
- starcoder2: ~1.7 GB
- codegemma: ~5 GB

**Total for all models**: ~30 GB

---

## Getting Help

1. **Check environment**: `./scripts/check_environment.sh`
2. **Read logs**: Check console output for detailed error messages
3. **Review documentation**: See `analysis/` directory for detailed reports
4. **Create GitHub issue**: Report bugs with full error output

---

## Next Steps

After installation:

1. **Run environment check**: `./scripts/check_environment.sh`
2. **Test single model**: `python3 auto_benchmark.py --model gpt-4o --retries 3`
3. **Review results**: Open `reports/gpt-4o_*.html` in browser
4. **Run full benchmark**: `python3 auto_benchmark.py --all --retries 3`
5. **Analyze results**: See `CURRENT_STATUS.md` for latest findings

---

## License

See LICENSE file for details.
