# Multi-Provider AI Security Benchmark Setup

The benchmark now supports three AI providers:
- **Ollama** (local models - free)
- **OpenAI** (GPT models - requires API key)
- **Anthropic Claude** (Claude models - requires API key)

## Installation

### 1. Install Python Dependencies

```bash
# For OpenAI support
pip install openai

# For Claude support
pip install anthropic

# Both
pip install openai anthropic
```

### 2. Set Up API Keys

#### OpenAI Setup

1. Get your API key from https://platform.openai.com/api-keys
2. Set the environment variable:

```bash
# Linux/Mac
export OPENAI_API_KEY='sk-your-key-here'

# Or add to ~/.bashrc or ~/.zshrc for persistence
echo "export OPENAI_API_KEY='sk-your-key-here'" >> ~/.bashrc
```

#### Anthropic Claude Setup

1. Get your API key from https://console.anthropic.com/settings/keys
2. Set the environment variable:

```bash
# Linux/Mac
export ANTHROPIC_API_KEY='sk-ant-your-key-here'

# Or add to ~/.bashrc or ~/.zshrc for persistence
echo "export ANTHROPIC_API_KEY='sk-ant-your-key-here'" >> ~/.bashrc
```

#### Ollama Setup (No API Key Required)

Ollama runs locally - no API key needed!

```bash
# Install from https://ollama.ai
# Or use homebrew on Mac
brew install ollama

# Pull models
ollama pull codellama
ollama pull deepseek-coder
ollama pull starcoder2
ollama pull codegemma
```

## Usage Examples

### Test with Ollama (Local, Free)

```bash
# CodeLlama
python3 auto_benchmark.py --model codellama

# DeepSeek Coder
python3 auto_benchmark.py --model deepseek-coder

# StarCoder2
python3 auto_benchmark.py --model starcoder2
```

### Test with OpenAI

```bash
# Ensure API key is set
export OPENAI_API_KEY='your-key-here'

# GPT-4 (most capable, more expensive)
python3 auto_benchmark.py --model gpt-4

# GPT-4 Turbo (faster, cheaper)
python3 auto_benchmark.py --model gpt-4-turbo-preview

# GPT-3.5 Turbo (fastest, cheapest)
python3 auto_benchmark.py --model gpt-3.5-turbo
```

### Test with Claude

```bash
# Ensure API key is set
export ANTHROPIC_API_KEY='your-key-here'

# Claude 3 Opus (most capable)
python3 auto_benchmark.py --model claude-3-opus-20240229

# Claude 3 Sonnet (balanced)
python3 auto_benchmark.py --model claude-3-sonnet-20240229

# Claude 3 Haiku (fastest, cheapest)
python3 auto_benchmark.py --model claude-3-haiku-20240307
```

### Quick Testing (Limit Prompts)

```bash
# Test with only 5 prompts (faster/cheaper for initial testing)
python3 auto_benchmark.py --model gpt-4 --limit 5
python3 auto_benchmark.py --model claude-3-opus-20240229 --limit 5
```

### Custom Output Directory

```bash
# Organize results by provider
python3 auto_benchmark.py --model gpt-4 --output generated_openai_gpt4
python3 auto_benchmark.py --model claude-3-opus-20240229 --output generated_claude_opus
```

## Model Recommendations

### OpenAI Models

| Model | Best For | Cost | Speed |
|-------|----------|------|-------|
| gpt-4 | Highest quality code | $$$ | Slow |
| gpt-4-turbo-preview | Good balance | $$ | Medium |
| gpt-3.5-turbo | Quick testing | $ | Fast |

### Claude Models

| Model | Best For | Cost | Speed |
|-------|----------|------|-------|
| claude-3-opus-20240229 | Highest quality code | $$$ | Slow |
| claude-3-sonnet-20240229 | Good balance | $$ | Medium |
| claude-3-haiku-20240307 | Quick testing | $ | Fast |

### Ollama Models (All Free & Local)

| Model | Best For | Notes |
|-------|----------|-------|
| deepseek-coder | Code generation | Good security awareness |
| codellama | General coding | Meta's specialized model |
| starcoder2 | Code completion | BigCode project |
| codegemma | Google Gemma | Smaller, faster |

## Cost Estimates (API Models)

**Note:** Prices are approximate and subject to change. Check current pricing:
- OpenAI: https://openai.com/pricing
- Anthropic: https://www.anthropic.com/pricing

### Per Benchmark Run (45 prompts, ~2000 tokens per prompt)

**OpenAI:**
- GPT-4: ~$1.50 - $3.00
- GPT-4 Turbo: ~$0.50 - $1.00
- GPT-3.5 Turbo: ~$0.10 - $0.20

**Claude:**
- Claude 3 Opus: ~$1.50 - $3.00
- Claude 3 Sonnet: ~$0.30 - $0.60
- Claude 3 Haiku: ~$0.05 - $0.10

**Tip:** Use `--limit 5` for initial testing to minimize costs!

## Comparing Results

After running benchmarks with different models, generate a comparison report:

```bash
# Run benchmarks
python3 auto_benchmark.py --model gpt-4
python3 auto_benchmark.py --model claude-3-opus-20240229
python3 auto_benchmark.py --model codellama
python3 auto_benchmark.py --model deepseek-coder

# Update generate_comparison_report.py with the new report paths
# Then generate comparison
python3 generate_comparison_report.py
```

## Troubleshooting

### OpenAI Errors

```
Error: OPENAI_API_KEY environment variable not set
```
**Solution:** Set the API key: `export OPENAI_API_KEY='your-key-here'`

```
Error: Incorrect API key provided
```
**Solution:** Verify your API key at https://platform.openai.com/api-keys

### Claude Errors

```
Error: ANTHROPIC_API_KEY environment variable not set
```
**Solution:** Set the API key: `export ANTHROPIC_API_KEY='your-key-here'`

### Ollama Errors

```
Error: Ollama is not running
```
**Solution:**
1. Install Ollama from https://ollama.ai
2. Start it: `ollama serve`
3. Or the script will try to auto-start

## Rate Limiting

The code generator includes automatic delays between API calls to respect rate limits:
- OpenAI/Claude: 1 second delay between requests
- Ollama: 0.5 second delay

If you hit rate limits, the API will return errors. Consider:
1. Using `--limit` to reduce number of prompts
2. Spreading tests across multiple days
3. Upgrading your API tier for higher limits
