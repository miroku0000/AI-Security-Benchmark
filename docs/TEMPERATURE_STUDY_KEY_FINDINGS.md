# Temperature Study: Key Findings

## Comparison: 66 Prompts (Python/JS) vs 140 Prompts (All Languages)

### Executive Summary

We analyzed 19 models across 5 temperature settings (0.0, baseline/0.2, 0.5, 0.7, 1.0) using two test sets:
- **66 prompts**: Original benchmark (Python + JavaScript only)
- **140 prompts**: Full benchmark (Python, JavaScript, Java, C#, C/C++, Go, Rust)

### Key Finding: Multi-Language Impact on Security Scores

**Models generally perform BETTER on multi-language prompts than Python/JS only:**

| Impact Category | Models | Average Difference | Notes |
|----------------|---------|-------------------|-------|
| **Strong Improvement** | Claude Sonnet 4.5, Qwen2.5-Coder, GPT-4 | +5% to +8% | Weakest on Python/JS, stronger on compiled languages |
| **Moderate Improvement** | GPT-5.4-mini, Gemini, DeepSeek-6.7b, CodeLlama, Llama3.1, Mistral, CodeGemma, GPT-3.5, GPT-4o-mini, GPT-4o | +2% to +5% | Consistent improvement across added languages |
| **Neutral** | GPT-5.4, Claude Opus 4.6 | ±0.5% | Consistent across languages |
| **Degradation** | StarCoder2, DeepSeek-Coder, GPT-5.2 | -0.5% to -7% | Code-specialized models worse on compiled languages |

### Top Performers by Test Set

#### 66 Prompts (Python/JS Only)
1. **StarCoder2 @ temp 1.0**: 77.9% (162/208)
2. **DeepSeek-Coder @ temp 0.7**: 76.9% (160/208)
3. **GPT-5.2 @ baseline**: 72.6% (151/208)

#### 140 Prompts (All Languages)
1. **DeepSeek-Coder @ temp 0.7**: 72.0% (252/350)
2. **StarCoder2 @ temp 1.0**: 70.9% (248/350)
3. **GPT-5.2 @ baseline**: 68.9% (241/350)

### Temperature Sensitivity Analysis

#### Highest Variation (66 Prompts)
1. **StarCoder2**: 15.4 pp variation (62.5% → 77.9%)
2. **DeepSeek-Coder**: 9.1 pp variation (67.8% → 76.9%)
3. **Claude Sonnet 4.5**: 9.1 pp variation (39.4% → 48.6%)

#### Highest Variation (140 Prompts)
1. **StarCoder2**: 8.6 pp variation (62.3% → 70.9%)
2. **DeepSeek-Coder**: 6.9 pp variation (65.1% → 72.0%)
3. **Claude Sonnet 4.5**: 5.1 pp variation (47.7% → 52.9%)

**Observation**: Multi-language expansion REDUCES temperature sensitivity (variation decreases by ~40% for code-specialized models).

### Language-Specific Patterns

#### Models Hurt by Compiled Languages (negative difference)
- **StarCoder2**: -7.0 pp at temp 1.0, -5.3 pp at temp 0.5
  - *Reason*: Code-specialized for Python/JS, weaker on Java/C#/Go/Rust

- **DeepSeek-Coder**: -4.9 pp at temp 0.7, -3.2 pp at temp 1.0
  - *Reason*: Same as StarCoder2, optimized for dynamic languages

- **GPT-5.2**: -3.7 pp at baseline
  - *Reason*: Strong general coding model, slightly weaker on type-strict languages

#### Models Helped by Compiled Languages (positive difference)
- **Claude Sonnet 4.5**: +8.3 pp at temp 0.7, +8.1 pp at temp 0.0
  - *Reason*: Better at memory safety and type systems (Rust, Go, C++)

- **GPT-4**: +6.5 pp at temp 0.7, +5.5 pp at baseline/temp 0.5
  - *Reason*: Stronger on enterprise languages (Java, C#)

- **Qwen2.5-Coder**: +6.6 pp at baseline, +5.9 pp at temp 0.5
  - *Reason*: Improved on statically-typed languages

### Temperature Recommendations by Model Type

#### Code-Specialized Models (StarCoder2, DeepSeek-Coder)
- **Best temperatures**: 0.7 - 1.0 (higher creativity improves security)
- **Python/JS**: Use temp 1.0 for maximum security (77.9%)
- **All languages**: Use temp 0.7 for best balance (72.0%)

#### General-Purpose Models (GPT-5.2, GPT-5.4, Claude Opus)
- **Best temperatures**: Baseline/0.2 (default works best)
- **Minimal variation**: ±3-7 pp across temperatures
- **Recommendation**: Stick with default settings

#### Weak Models (GPT-3.5, GPT-4o-mini, CodeGemma)
- **Best temperatures**: 0.5 - 0.7 (moderate creativity)
- **Pattern**: Compiled languages help more than temperature tuning
- **Improvement**: +2-5 pp from multi-language prompts

### Research Implications

1. **Language diversity matters**: Expanding from 2 to 7 languages revealed that:
   - Most models are better at compiled languages (memory safety, type systems)
   - Code-specialized models are optimized for dynamic languages
   - Temperature sensitivity is language-dependent

2. **Temperature is a security parameter**:
   - StarCoder2 improves 15.4 pp on Python/JS with temp tuning
   - Effect diminishes with language diversity (8.6 pp across all languages)
   - Different optimal temperatures for different language families

3. **Baseline rankings change**:
   - **Python/JS only**: StarCoder2 > DeepSeek-Coder > GPT-5.2
   - **All languages**: DeepSeek-Coder > StarCoder2 > GPT-5.2
   - Code-specialized models lose advantage on compiled languages

### Conclusion

The multi-language expansion (66 → 140 prompts) revealed:
- **Temperature tuning is most effective for Python/JavaScript** (15.4 pp variation)
- **Compiled languages reduce temperature sensitivity** (variation drops to 8.6 pp)
- **Most models improve +2-8% on compiled languages** (better type safety, memory management)
- **Code-specialized models degrade -2-7%** on compiled languages (training bias toward dynamic languages)

This suggests that **language choice affects security scores more than temperature** for most models, with the exception of code-specialized models (StarCoder2, DeepSeek-Coder) where temperature tuning provides significant gains on Python/JavaScript workloads.
