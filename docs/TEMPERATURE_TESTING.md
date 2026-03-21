# Temperature Testing Guide

## Overview

This guide explains how to test AI models at different temperature settings to understand how randomness affects security in generated code.

## What is Temperature?

Temperature is a parameter that controls the randomness of AI model outputs:

- **Temperature 0.0**: Deterministic, always picks the most likely next token
- **Temperature 0.2**: Low randomness, focused and consistent (DEFAULT)
- **Temperature 0.5**: Moderate randomness, balanced creativity
- **Temperature 0.7**: Higher randomness, more creative/varied
- **Temperature 1.0**: High randomness, very diverse outputs

## Why Test at Different Temperatures?

Understanding temperature's impact on security helps answer questions like:

1. **Does higher creativity lead to more vulnerabilities?**
   - Do models write less secure code when allowed more freedom?

2. **Does deterministic output guarantee security?**
   - Are low-temperature outputs always more secure?

3. **Which temperature is optimal for security?**
   - What's the sweet spot between functionality and security?

4. **How consistent are security patterns?**
   - Do the same vulnerabilities appear across temperatures?

## Running Benchmarks at Different Temperatures

### Single Model at Specific Temperature

```bash
# Test GPT-4o at temperature 0.7
python3 auto_benchmark.py --model gpt-4o --temperature 0.7

# Test at high temperature (1.0)
python3 auto_benchmark.py --model gpt-4o --temperature 1.0

# Test at low temperature (0.0) - deterministic
python3 auto_benchmark.py --model gpt-4o --temperature 0.0
```

### Comprehensive Temperature Study

Test a model across multiple temperatures:

```bash
# Run the same model at 4 different temperatures
python3 auto_benchmark.py --model gpt-4o --temperature 0.2  # Baseline (default)
python3 auto_benchmark.py --model gpt-4o --temperature 0.5  # Moderate
python3 auto_benchmark.py --model gpt-4o --temperature 0.7  # High
python3 auto_benchmark.py --model gpt-4o --temperature 1.0  # Maximum
```

### Testing All Models at Non-Default Temperature

```bash
# Test all models at temperature 0.7
python3 auto_benchmark.py --all --temperature 0.7
```

## Output Organization

Generated code and reports are automatically organized by temperature:

```
output/
├── gpt-4o/              # Default temp (0.2)
├── gpt-4o_temp0.5/      # Temperature 0.5
├── gpt-4o_temp0.7/      # Temperature 0.7
└── gpt-4o_temp1.0/      # Temperature 1.0

reports/
├── gpt-4o_208point_20260320.json              # Default temp
├── gpt-4o_temp0.5_208point_20260320.json      # Temperature 0.5
├── gpt-4o_temp0.7_208point_20260320.json      # Temperature 0.7
└── gpt-4o_temp1.0_208point_20260320.json      # Temperature 1.0
```

## Temperature Metadata in Reports

All JSON reports now include temperature metadata:

```json
{
  "benchmark_date": "2026-03-20T10:30:00",
  "model_name": "gpt-4o",
  "temperature": 0.7,
  "summary": {
    "overall_score": "145/208",
    "percentage": 69.7
  }
}
```

## Analyzing Temperature Impact

Use the temperature impact analysis script to compare results:

```bash
# Analyze all models with temperature variants
python3 analysis/analyze_temperature_impact.py

# Analyze specific model
python3 analysis/analyze_temperature_impact.py --model gpt-4o

# Save report to file
python3 analysis/analyze_temperature_impact.py --output temp_analysis.txt
```

### Sample Analysis Output

```
================================================================================
MODEL: gpt-4o
================================================================================

Temperature Variants:
Temp     Score           Secure   Partial  Vulnerable   Percentage
--------------------------------------------------------------------------------
0.2      145/208         52       12       2            69.7%
0.5      142/208         48       14       4            68.3%
0.7      138/208         45       13       8            66.3%
1.0      130/208         40       15       11           62.5%

Impact Summary:
  Temperature Range: 0.2 - 1.0
  Security Score Change: 7.2 percentage points
  Vulnerable Count Change: 9
  Best Performance: 0.2 (69.7%)
  Worst Performance: 1.0 (62.5%)
  → Higher temperature appears to INCREASE vulnerabilities for this model

Vulnerability Types by Temperature:
Vuln Type                           T=0.2  T=0.5  T=0.7  T=1.0
--------------------------------------------------------------------------------
HARDCODED_SECRET                       3      4      5      7
SQL_INJECTION                          2      2      3      4
XSS                                    1      2      3      4
```

## Reproducibility Notes

### Temperature and Reproducibility

- **Temperature 0.0**: Most reproducible (same input = same output)
- **Temperature > 0.0**: Less reproducible (same input = different outputs)
- **Caching**: Results are cached by model AND temperature

### Re-running Tests

```bash
# Use cached results (default)
python3 auto_benchmark.py --model gpt-4o --temperature 0.7

# Force regenerate (ignore cache)
python3 auto_benchmark.py --model gpt-4o --temperature 0.7 --force-regenerate
```

## Special Cases

### OpenAI o-series Models

**IMPORTANT**: OpenAI's o-series models (o1, o3, o4) do **not** support custom temperature settings. These models use fixed internal parameters.

When running these models with a temperature parameter, the value will be recorded but not applied:

```bash
# Temperature will be ignored (o-series limitation)
python3 auto_benchmark.py --model o3 --temperature 0.7
```

The report will show `temperature: null` for o-series models.

### Local Models (Ollama)

Most Ollama models support temperature, but effectiveness varies:

```bash
# Test local model at different temperatures
python3 auto_benchmark.py --model codellama --temperature 0.7
python3 auto_benchmark.py --model deepseek-coder --temperature 0.5
```

## Research Questions

Use temperature testing to investigate:

### 1. Temperature vs Vulnerability Rate

**Hypothesis**: Higher temperature → more vulnerabilities

**Test**:
```bash
for temp in 0.0 0.2 0.5 0.7 1.0; do
  python3 auto_benchmark.py --model gpt-4o --temperature $temp
done
python3 analysis/analyze_temperature_impact.py --model gpt-4o
```

### 2. Vulnerability Type Patterns

**Question**: Do certain vulnerability types appear more at specific temperatures?

**Analysis**: Compare `vulnerability_types` across temperatures in the analysis report

### 3. Model Sensitivity

**Question**: Which models are most affected by temperature changes?

**Test**:
```bash
# Test multiple models at two extremes
for model in gpt-4o claude-opus-4-6 gemini-2.5-flash; do
  python3 auto_benchmark.py --model $model --temperature 0.2
  python3 auto_benchmark.py --model $model --temperature 1.0
done

# Compare
python3 analysis/analyze_temperature_impact.py
```

### 4. Security vs Functionality Trade-off

**Question**: Does the most secure temperature produce the most functional code?

**Manual Review**: Compare code quality across temperatures for the same prompt

## Best Practices

1. **Baseline First**: Always run at default temperature (0.2) first
2. **Multiple Runs**: For temp > 0, consider multiple runs to account for variance
3. **Document Findings**: Record observations about code quality vs security
4. **Compare Extremes**: Test at 0.0 and 1.0 to see maximum range of impact
5. **Category Analysis**: Some vulnerability categories may be more temperature-sensitive

## Quick Start Example

Complete temperature study for a single model:

```bash
# 1. Run at multiple temperatures
python3 auto_benchmark.py --model gpt-4o --temperature 0.2
python3 auto_benchmark.py --model gpt-4o --temperature 0.5
python3 auto_benchmark.py --model gpt-4o --temperature 0.7
python3 auto_benchmark.py --model gpt-4o --temperature 1.0

# 2. Analyze impact
python3 analysis/analyze_temperature_impact.py --model gpt-4o --output gpt4o_temp_study.txt

# 3. Review results
cat gpt4o_temp_study.txt
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Temperature ignored" warning | Normal for o-series models, they don't support custom temperature |
| Same vulnerabilities at all temps | Try wider temperature range (0.0 to 1.0) |
| No temperature in report | Update to latest version, older reports don't have this field |
| Analysis shows no data | Ensure you've run benchmarks at multiple temperatures first |
| Inconsistent results | Run multiple times for temperatures > 0.2 to account for randomness |

## References

- [OpenAI Temperature Documentation](https://platform.openai.com/docs/api-reference/chat/create#temperature)
- [Anthropic Temperature Guide](https://docs.anthropic.com/claude/docs/temperature)
- Main benchmark README: [../README.md](../README.md)
- Analysis scripts: [../analysis/](../analysis/)
