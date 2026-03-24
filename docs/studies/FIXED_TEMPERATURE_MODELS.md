# Fixed Temperature Models

## Overview
Some AI models do not support custom temperature settings and use their default/fixed temperature values. The benchmark system automatically handles these models by omitting the temperature parameter from API calls.

## Models with Fixed Temperature

### OpenAI Reasoning Models
These models use a fixed temperature and do not accept custom temperature parameters:

- **o1** - OpenAI's reasoning model (default temp: 1.0)
- **o3** - Advanced reasoning model (default temp: 1.0)
- **o3-mini** - Smaller reasoning model (default temp: 1.0)

### Code-Specific Tools
These models/tools use their own optimized temperature settings:

- **cursor** - Cursor AI editor (uses internal default)
- **codex-app** - Codex application (uses internal default)

## Implementation Details

The `code_generator.py` automatically detects these models and handles them appropriately:

```python
# In _generate_openai() method (lines 239-257)
is_o_series = model_lower.startswith('o1') or model_lower.startswith('o3') or model_lower.startswith('o4')
is_fixed_temp = 'cursor' in model_lower or 'codex' in model_lower

if is_o_series or is_fixed_temp:
    # Don't include temperature parameter
    params = {
        "model": self.model,
        "messages": [...],
        "max_completion_tokens": 4096
    }
```

## Temperature Study Exclusion

When running temperature studies (testing models at 0.0, 0.5, 0.7, 1.0), these models should be:

1. **Excluded from multi-temperature testing** - No point testing different temperatures
2. **Run only once** - Single baseline run at their default temperature
3. **Documented separately** - Listed as "fixed temperature" models

## Directory Structure

Fixed temperature models have a single output directory without temperature suffix:

```
output/
├── o1/                    # Single directory (not o1_temp0.0, o1_temp0.5, etc.)
├── o3/
├── o3-mini/
├── cursor/
└── codex-app/
```

## Benchmark Reports

When generating reports, these models should be:

- Listed in a separate "Fixed Temperature Models" section
- Not included in temperature comparison charts
- Documented with their default temperature value
- Compared against configurable models at their default temp (typically 0.2-1.0)

## Usage Examples

```bash
# Correct: Run with any temperature value (will be ignored)
python3 code_generator.py --model o1 --temperature 0.5

# Also correct: Default temperature will be used
python3 code_generator.py --model o3

# Fixed temperature models in temperature study (should be excluded or run once)
# The temperature study script should skip these models
./run_temperature_study.sh
```

## Notes

- The temperature parameter can still be passed to these models without error
- The code silently ignores the temperature parameter for these models
- This ensures consistent behavior across all model types
- Users don't need to remember which models support temperature control

---

Last updated: March 22, 2026
