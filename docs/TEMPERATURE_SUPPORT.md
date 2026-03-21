# Temperature Support by Model

## Summary Table

| Provider | Models | Temperature Support | Notes |
|----------|--------|---------------------|-------|
| **OpenAI (GPT series)** | gpt-3.5-turbo, gpt-4, gpt-4o, gpt-4o-mini, chatgpt-4o-latest, gpt-5.2, gpt-5.4, gpt-5.4-mini | ✅ **YES** | Full support (0.0 - 2.0) |
| **OpenAI (o-series)** | o1, o3, o3-mini | ❌ **NO** | Fixed temperature=1.0 (OpenAI limitation) |
| **Anthropic (Claude)** | claude-opus-4-6, claude-sonnet-4-5 | ✅ **YES** | Full support (0.0 - 1.0) |
| **Google (Gemini)** | gemini-2.5-flash | ✅ **YES** | Full support (0.0 - 2.0) |
| **Ollama (Local)** | codellama, deepseek-coder, starcoder2, codegemma, mistral, llama3.1, qwen2.5-coder | ✅ **YES** | Requires `ollama` Python library |

## Detailed Breakdown

### ✅ Models That Support Temperature

#### OpenAI GPT Series (11 models)
```bash
# These models fully support temperature parameter:
- gpt-3.5-turbo
- gpt-4
- gpt-4o
- gpt-4o-mini
- chatgpt-4o-latest
- gpt-5.2
- gpt-5.4
- gpt-5.4-mini
```

**Usage:**
```bash
python3 auto_benchmark.py --model gpt-4o --temperature 0.7 --retries 3
python3 auto_benchmark.py --model gpt-5.4 --temperature 0.5 --retries 3
```

**Valid Range**: 0.0 - 2.0 (though values above 1.0 are rarely useful)

---

#### Anthropic Claude (2 models)
```bash
# These models fully support temperature parameter:
- claude-opus-4-6
- claude-sonnet-4-5
```

**Usage:**
```bash
python3 auto_benchmark.py --model claude-opus-4-6 --temperature 0.7 --retries 3
python3 auto_benchmark.py --model claude-sonnet-4-5 --temperature 0.5 --retries 3
```

**Valid Range**: 0.0 - 1.0

---

#### Google Gemini (1 model)
```bash
# This model supports temperature parameter:
- gemini-2.5-flash
```

**Usage:**
```bash
python3 auto_benchmark.py --model gemini-2.5-flash --temperature 0.7 --retries 3
```

**Valid Range**: 0.0 - 2.0

---

### ❌ Models That Do NOT Support Temperature

#### OpenAI o-series (3 models)
```bash
# These models have FIXED temperature=1.0 (OpenAI API limitation):
- o1
- o3
- o3-mini
```

**Why?** OpenAI's o-series models use a different reasoning architecture that doesn't support custom temperature settings. They always use temperature=1.0.

**What Happens?**
- You can specify `--temperature 0.7` but it will be **ignored**
- The report will show `"temperature": null` for these models
- Code generation uses the model's default (1.0)

**Usage (temperature ignored):**
```bash
python3 auto_benchmark.py --model o3 --temperature 0.7 --retries 3
# Temperature is ignored, model uses fixed 1.0
```

**From code_generator.py (lines 213-227):**
```python
is_o_series = model_lower.startswith('o1') or model_lower.startswith('o3') or model_lower.startswith('o4')

if 'gpt-5' in model_lower or is_o_series:
    params = {
        "model": self.model,
        "messages": [...],
        "max_completion_tokens": 4096
    }
    # Only add temperature for non-o-series models
    if not is_o_series:
        params["temperature"] = self.temperature
```

---

#### Ollama Local Models (9 models) ✅ NOW SUPPORTED!
```bash
# These models now support temperature (requires ollama Python library):
- codellama
- deepseek-coder
- deepseek-coder:6.7b-instruct
- starcoder2
- codegemma
- mistral
- llama3.1
- qwen2.5-coder
- qwen2.5-coder:14b
```

**Requirements:**
```bash
pip install ollama
```

**How it Works:**
The code automatically uses the `ollama` Python library if installed. If not installed, it falls back to `ollama run` command (without temperature support) with a warning.

```python
# With ollama library installed (temperature supported):
import ollama
response = ollama.generate(
    model=self.model,
    prompt=prompt,
    options={'temperature': self.temperature}
)

# Without library (fallback - no temperature):
subprocess.run(['ollama', 'run', self.model], ...)
```

**Usage (with ollama library installed):**
```bash
python3 auto_benchmark.py --model codellama --temperature 0.7 --retries 3
# Temperature IS applied!
```

**Valid Range**: 0.0 - 2.0 (Ollama supports same range as OpenAI models)

---

## Testing Temperature Support

### Models You Can Test at Different Temperatures

**Total: 23 models** support temperature (all except o-series!)

**OpenAI (8 models):**
```bash
for temp in 0.0 0.2 0.5 0.7; do
  python3 auto_benchmark.py --model gpt-4o --temperature $temp --retries 3
done
```

**Claude (2 models):**
```bash
for temp in 0.0 0.2 0.5 0.7; do
  python3 auto_benchmark.py --model claude-opus-4-6 --temperature $temp --retries 3
done
```

**Gemini (1 model):**
```bash
for temp in 0.0 0.2 0.5 0.7; do
  python3 auto_benchmark.py --model gemini-2.5-flash --temperature $temp --retries 3
done
```

**Ollama (9 models) - NEW!:**
```bash
# Install ollama library first
pip install ollama

# Test temperature with Ollama models
for temp in 0.0 0.2 0.5 0.7; do
  python3 auto_benchmark.py --model codellama --temperature $temp --retries 3
done

for temp in 0.0 0.2 0.5 0.7; do
  python3 auto_benchmark.py --model starcoder2 --temperature $temp --retries 3
done
```

### Full Temperature Study Script

Test all temperature-supporting models:

```bash
#!/bin/bash
TEMPS=(0.0 0.2 0.5 0.7)

# OpenAI models (that support temperature)
OPENAI=(gpt-3.5-turbo gpt-4 gpt-4o gpt-4o-mini chatgpt-4o-latest gpt-5.2 gpt-5.4 gpt-5.4-mini)

# Claude models
CLAUDE=(claude-opus-4-6 claude-sonnet-4-5)

# Gemini models
GEMINI=(gemini-2.5-flash)

# Ollama models (NEW! - requires pip install ollama)
OLLAMA=(codellama deepseek-coder starcoder2 codegemma mistral llama3.1 qwen2.5-coder)

for model in "${OPENAI[@]}" "${CLAUDE[@]}" "${GEMINI[@]}" "${OLLAMA[@]}"; do
  for temp in "${TEMPS[@]}"; do
    echo "Testing $model at temperature $temp"
    python3 auto_benchmark.py --model "$model" --temperature "$temp" --retries 3
  done
done
```

---

## Recommended Temperature Values

Based on our testing with GPT-4o:

| Temperature | Security Score | Use Case |
|-------------|---------------|----------|
| **0.0** | 43.8% (worst) | Deterministic, most predictable |
| **0.2** | 45.7% | Default, balanced |
| **0.5** | 45.2% | Moderate creativity |
| **0.7** | 47.1% (best) | Higher creativity, best security for GPT-4o |

**Note**: Results vary by model. Always test your specific model.

---

## Quick Reference

**Test a model with temperature:**
```bash
python3 auto_benchmark.py --model <model-name> --temperature <0.0-1.0> --retries 3
```

**Analyze temperature impact:**
```bash
python3 analysis/analyze_temperature_impact.py --model <model-name>
```

**Check if a model supports temperature:**
- OpenAI GPT series: ✅ YES
- OpenAI o-series: ❌ NO (fixed 1.0)
- Anthropic Claude: ✅ YES
- Google Gemini: ✅ YES
- Ollama models: ✅ YES (requires `pip install ollama`)
