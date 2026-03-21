# Ollama Temperature Support - Implementation Update

## What Changed

Ollama models now **support temperature parameter** for code generation! This enables temperature testing for all 9 Ollama models in the benchmark.

## Summary

- **Previously**: Ollama models used `ollama run` command → no temperature control
- **Now**: Uses `ollama` Python library → full temperature support (0.0 - 2.0)
- **Fallback**: If library not installed, falls back to command-line with warning

## Models Now Supporting Temperature

All 9 Ollama models now support temperature:

1. codellama
2. deepseek-coder
3. deepseek-coder:6.7b-instruct
4. starcoder2
5. codegemma
6. mistral
7. llama3.1
8. qwen2.5-coder
9. qwen2.5-coder:14b

**Total models with temperature support**: **23 out of 26** (88%)

Only OpenAI o-series models (o1, o3, o3-mini) don't support temperature due to API limitations.

## Installation

Add the ollama Python library to your environment:

```bash
pip install ollama
```

Or using requirements.txt:

```bash
pip install -r requirements.txt
```

The library is now included in `requirements.txt`.

## Usage

### Basic Usage

```bash
# Test codellama at different temperatures
python3 auto_benchmark.py --model codellama --temperature 0.0 --retries 3
python3 auto_benchmark.py --model codellama --temperature 0.2 --retries 3
python3 auto_benchmark.py --model codellama --temperature 0.5 --retries 3
python3 auto_benchmark.py --model codellama --temperature 0.7 --retries 3

# Analyze temperature impact
python3 analysis/analyze_temperature_impact.py --model codellama
```

### Temperature Study for Ollama Model

```bash
#!/bin/bash
# Test StarCoder2 at multiple temperatures

TEMPS=(0.0 0.2 0.5 0.7)

for temp in "${TEMPS[@]}"; do
  echo "Testing starcoder2 at temperature $temp"
  python3 auto_benchmark.py --model starcoder2 --temperature "$temp" --retries 3
done

# Analyze results
python3 analysis/analyze_temperature_impact.py --model starcoder2
```

## Technical Implementation

### Code Changes (code_generator.py)

The `_generate_ollama()` method now:

1. **Tries to import ollama library**
   - If successful: Uses `ollama.generate()` with temperature option
   - If ImportError: Falls back to `subprocess.run()` with warning

2. **Temperature is passed via options**
   ```python
   response = ollama.generate(
       model=self.model,
       prompt=enhanced_prompt,
       options={
           'temperature': self.temperature,
           'num_predict': 4096,
       }
   )
   ```

3. **Graceful degradation**
   - Without library: User sees warning, generation continues without temperature
   - With library: Full temperature support

### Behavior Matrix

| Scenario | ollama Library | Temperature | Behavior |
|----------|---------------|-------------|----------|
| **Ideal** | ✅ Installed | 0.7 | Uses library, applies temperature |
| **Fallback** | ❌ Not installed | 0.7 | Uses subprocess, shows warning, ignores temperature |
| **Default** | ✅ Installed | 0.2 (default) | Uses library, applies default temperature |

## Example Output

### With ollama Library Installed

```
======================================================================
AI Code Generator
======================================================================
Provider: ollama
Model: codellama
Temperature: 0.7
Timeout: 300s
Caching: Enabled
Total prompts: 66
Output directory: output/codellama_temp0.7
======================================================================
[1/66] sql_001 (sql_injection, python)...
  Saved to output/codellama_temp0.7/sql_001.py
[2/66] sql_002 (sql_injection, javascript)...
  Saved to output/codellama_temp0.7/sql_002.js
```

### Without ollama Library (Fallback)

```
======================================================================
AI Code Generator
======================================================================
Provider: ollama
Model: codellama
Temperature: 0.7
...
======================================================================
[1/66] sql_001 (sql_injection, python)...
WARNING  ollama library not installed (pip install ollama) - temperature not supported
WARNING  Falling back to subprocess method without temperature control
  Saved to output/codellama_temp0.7/sql_001.py
```

## Benefits

### 1. Research Capabilities

Can now study temperature impact on **all** code generation models (except o-series):

```bash
# Compare temperature effects across providers
python3 auto_benchmark.py --model gpt-4o --temperature 0.7 --retries 3
python3 auto_benchmark.py --model claude-opus-4-6 --temperature 0.7 --retries 3
python3 auto_benchmark.py --model starcoder2 --temperature 0.7 --retries 3

# Analyze all three
python3 analysis/analyze_temperature_impact.py --model gpt-4o
python3 analysis/analyze_temperature_impact.py --model claude-opus-4-6
python3 analysis/analyze_temperature_impact.py --model starcoder2
```

### 2. Fair Comparisons

Can now compare models at the **same temperature** for fair security benchmarking:

```bash
# All at temperature 0.5
python3 auto_benchmark.py --model gpt-4o --temperature 0.5 --retries 3
python3 auto_benchmark.py --model claude-opus-4-6 --temperature 0.5 --retries 3
python3 auto_benchmark.py --model codellama --temperature 0.5 --retries 3
```

### 3. Consistency

Temperature values are now:
- Tracked in cache (different temps = separate cache entries)
- Stored in reports (JSON includes `"temperature": 0.7`)
- Reflected in directory names (`output/codellama_temp0.7`)

## Testing Temperature Impact on Local Models

Previous research showed surprising results for GPT-4o:
- Temperature 0.0 (deterministic): **43.8%** security score (worst)
- Temperature 0.7 (creative): **47.1%** security score (best)

Now you can research whether this pattern holds for local models:

```bash
# Does temperature affect StarCoder2 security similarly to GPT-4o?
for temp in 0.0 0.2 0.5 0.7; do
  python3 auto_benchmark.py --model starcoder2 --temperature $temp --retries 3
done

python3 analysis/analyze_temperature_impact.py --model starcoder2 --output starcoder2_temp_study.txt
```

## Files Modified

1. **code_generator.py** - Updated `_generate_ollama()` method
2. **requirements.txt** - Added `ollama>=0.1.0`
3. **docs/TEMPERATURE_SUPPORT.md** - Updated to reflect Ollama support
4. **docs/OLLAMA_TEMPERATURE_UPDATE.md** - This document

## Backward Compatibility

✅ **Fully backward compatible**

- Existing code without `ollama` library continues to work
- Graceful fallback with clear warning message
- No breaking changes to API or CLI

## Next Steps

### For Users

1. **Install ollama library**:
   ```bash
   pip install ollama
   ```

2. **Test your favorite Ollama model**:
   ```bash
   python3 auto_benchmark.py --model codellama --temperature 0.7 --retries 3
   ```

3. **Compare temperature effects**:
   ```bash
   python3 analysis/analyze_temperature_impact.py --model codellama
   ```

### For Researchers

Investigate questions like:
- Do local models show same temperature-security patterns as API models?
- Which Ollama model is most sensitive to temperature changes?
- Is there an optimal temperature for security across all models?

## Troubleshooting

**Problem**: Warning about ollama library not installed

**Solution**:
```bash
pip install ollama
# or
pip install -r requirements.txt
```

**Problem**: `ollama.generate()` connection error

**Solution**: Ensure Ollama is running:
```bash
ollama serve
# or just run any ollama command to auto-start
ollama list
```

**Problem**: Different results at same temperature

**Solution**: This is expected! Temperature > 0.0 introduces randomness. For reproducibility:
- Use temperature 0.0 for deterministic results
- Run multiple times and average results
- Use `--force-regenerate` to ignore cache

## Conclusion

With this update, **23 out of 26 benchmark models** (88%) now support temperature testing. This enables comprehensive research into how temperature affects security across different providers and model architectures.

The implementation is backward compatible, gracefully degrades when the library isn't available, and maintains all existing caching and reporting functionality.
