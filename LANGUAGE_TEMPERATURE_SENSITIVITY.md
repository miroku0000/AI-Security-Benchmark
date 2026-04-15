# Language-Specific Temperature Sensitivity Analysis

## Executive Summary

We analyzed how temperature tuning affects security scores independently for each programming language across 10 models with temperature studies (deepseek-coder, starcoder2, gpt-5.2, claude-opus-4-6, gpt-5.4, gemini-2.5-flash, gpt-5.4-mini, codellama, deepseek-coder_6.7b-instruct, mistral).

## Key Finding: JavaScript is Most Temperature-Sensitive

**Average Temperature Variation by Language** (across all 10 models):

| Rank | Language   | Avg Variation | # Prompts | Notes |
|------|------------|---------------|-----------|-------|
| 1    | **JavaScript** | **12.3 pp** | 23 | Highest temperature sensitivity |
| 2    | **Go**         | **11.4 pp** | 15 | Tied for second |
| 2    | **Rust**       | **11.4 pp** | 14 | Tied for second |
| 4    | Java       | 11.1 pp | 15 | Moderate-high sensitivity |
| 5    | C#         | 10.4 pp | 15 | Moderate sensitivity |
| 6    | C/C++      | 10.0 pp | 15 | Moderate sensitivity |
| 7    | **Python**     | **8.6 pp** | 43 | **LOWEST temperature sensitivity** |

## Surprising Finding: Python vs JavaScript

Despite both being dynamic languages, **JavaScript shows 43% higher temperature sensitivity** than Python (12.3 pp vs 8.6 pp). This suggests that temperature tuning is MORE important for JavaScript security than Python.

## Language-Specific Patterns

### JavaScript (12.3 pp variation)
**Highest Temperature Sensitivity Across Models:**
- **Gemini 2.5 Flash**: 21.4 pp variation (48.2% @ temp 0.0 → 69.6% @ temp 1.0)
- **DeepSeek-Coder**: 16.1 pp variation (57.1% @ temp 0.5 → 73.2% @ temp 1.0)
- **CodeLlama**: 16.1 pp variation (35.7% @ temp 0.7 → 51.8% @ temp 0.0)

**Insight**: JavaScript security is highly temperature-dependent, especially for code-specialized models.

### Python (8.6 pp variation)
**Most Stable Language:**
- **DeepSeek-Coder**: 10.5 pp variation (69.1% @ baseline → 79.6% @ temp 0.7)
- **StarCoder2**: 16.4 pp variation (61.8% @ temp 0.0 → 78.3% @ temp 1.0)
- **Claude Opus 4.6**: Only 3.3 pp variation (61.2% @ baseline → 64.5% @ temp 0.0)

**Insight**: Python security scores are more stable across temperatures, with less need for tuning.

### Go & Rust (11.4 pp variation each)
**High Variation in Compiled Languages:**

**Go:**
- **DeepSeek-Coder**: 21.4 pp variation (50.0% @ baseline → 75.0% @ temp 0.5)
- **StarCoder2**: 21.4 pp variation (50.0% @ baseline → 71.4% @ temp 1.0)
- **Gemini 2.5 Flash**: 17.9 pp variation

**Rust:**
- **DeepSeek-Coder 6.7B**: 21.4 pp variation (57.1% @ temp 0.0 → 78.6% @ temp 1.0)
- **DeepSeek-Coder**: 17.9 pp variation (60.7% @ baseline → 78.6% @ temp 0.0)
- **Gemini 2.5 Flash**: 14.3 pp variation

**Insight**: Memory-safe languages (Go, Rust) show high temperature sensitivity, suggesting temperature affects how models handle safety features.

### Compiled Languages (Java, C#, C++)
**Moderate Temperature Sensitivity:**
- **Java**: 11.1 pp average (StarCoder2: 17.9 pp variation)
- **C#**: 10.4 pp average (Mistral: 21.4 pp variation, GPT-5.4/Gemini: 14.3 pp)
- **C++**: 10.0 pp average (Claude Opus/DeepSeek/CodeLlama: 13.3 pp)

**Insight**: Type-strict languages show moderate sensitivity, less than dynamic JavaScript but more than Python.

## Model-Specific Insights

### DeepSeek-Coder: Language-Dependent Temperature Effects
- **Python**: Best at temp 0.7 (79.6%), 10.5 pp variation
- **JavaScript**: Best at temp 1.0 (73.2%), 16.1 pp variation
- **Go**: Best at temp 0.5 (75.0%), 21.4 pp variation
- **Rust**: Best at temp 0.0/1.0 (78.6%), 17.9 pp variation

**Takeaway**: Different languages need different temperatures for the same model.

### StarCoder2: High Variation on Dynamic Languages
- **Python**: 16.4 pp variation (61.8% → 78.3%)
- **JavaScript**: 12.5 pp variation (64.3% → 76.8%)
- **Java**: 17.9 pp variation (39.3% → 57.1%)

**Takeaway**: Code-specialized models benefit most from temperature tuning.

### GPT-5.4: Minimal Rust Variation
- **Rust**: 0.0 pp variation (82.1% at ALL temperatures)
- **Python**: 6.6 pp variation
- **C#**: 14.3 pp variation (highest for GPT-5.4)

**Takeaway**: GPT-5.4 is remarkably consistent on Rust regardless of temperature.

### Claude Opus 4.6: Lowest Python Sensitivity
- **Python**: Only 3.3 pp variation (61.2% → 64.5%)
- **JavaScript**: 10.7 pp variation (60.7% → 71.4%)
- **C++**: 13.3 pp variation (73.3% → 86.7%)

**Takeaway**: Claude is most stable on Python, more variable on compiled languages.

## Practical Recommendations

### For JavaScript Development
**Temperature tuning is CRITICAL:**
- Use temp 0.7-1.0 for code-specialized models (DeepSeek-Coder, StarCoder2)
- Expect 12-16 pp improvement from optimal temperature
- JavaScript shows highest sensitivity to temperature parameter

### For Python Development
**Temperature tuning is LESS critical:**
- Python is most stable language (8.6 pp average variation)
- Default/baseline temperatures work well for most models
- Focus on model selection over temperature tuning

### For Go/Rust Development
**Temperature tuning matters for safety:**
- Use temp 0.0-0.5 for DeepSeek-Coder on Go (75.0% at temp 0.5)
- Use temp 0.0 or 1.0 for Rust (both 78.6% for DeepSeek-Coder)
- Memory-safe languages show 11.4 pp average variation

### For Enterprise Languages (Java, C#)
**Moderate temperature tuning needed:**
- Java: ~11 pp variation, tune for 50-57% security
- C#: ~10 pp variation, tune for 50-64% security
- Test multiple temperatures to find optimal settings

## Research Implications

1. **Language semantics affect temperature sensitivity**: Dynamic JavaScript is more temperature-sensitive than dynamic Python, suggesting that language features (typing, safety mechanisms) interact with temperature in complex ways.

2. **Temperature is a language-specific parameter**: The optimal temperature for JavaScript (often 1.0) differs from Python (often 0.7), Go (often 0.5), and Rust (varies by model).

3. **Memory-safe languages need careful tuning**: Go and Rust show high variation (11.4 pp), suggesting temperature affects how models handle safety guarantees.

4. **Model training affects language sensitivity**: Code-specialized models (StarCoder2, DeepSeek-Coder) show higher variation than general models, especially on Python/JavaScript.

## Conclusion

**JavaScript is the most temperature-sensitive language** (12.3 pp average variation), while **Python is the most stable** (8.6 pp). This 43% difference suggests that:

- JavaScript developers should ALWAYS tune temperature for optimal security
- Python developers can rely more on default settings
- Compiled languages (Go, Rust, Java, C#, C++) fall in between
- Temperature is not a universal parameter—it must be tuned per language

This finding challenges the assumption that temperature affects all languages equally and suggests that **temperature tuning should be language-aware**.
