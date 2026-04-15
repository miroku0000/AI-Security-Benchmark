# Temperature Quick Reference Guide for Secure Code Generation

## TL;DR: Language-Specific Temperature Recommendations

**Use this table to maximize security scores:**

| Language   | Recommended Temperature | Rationale |
|------------|------------------------|-----------|
| **JavaScript** | **temp 1.0** | 9/19 models optimal at 1.0 (higher creativity needed) |
| **Python** | **temp 0.5** | 7/19 models optimal at 0.5 (balanced approach) |
| **Java** | **temp 0.0** | 8/19 models optimal at 0.0 (deterministic is best) |
| **C#** | **temp 0.0** | 12/19 models optimal at 0.0 (strongly prefer deterministic) |
| **C++** | **temp 0.0** | 10/19 models optimal at 0.0 (memory safety needs precision) |
| **Go** | **temp 0.0** | 8/19 models optimal at 0.0 (consistency over creativity) |
| **Rust** | **temp 0.0** | 8/19 models optimal at 0.0 (safety-critical language) |

## Model-Language Optimal Temperature Matrix

Copy this table for quick lookup when configuring your AI code generator:

```
Model                          | Python       | JavaScript   | Java         | C#           | C++          | Go           | Rust
------------------------------|--------------|--------------|--------------|--------------|--------------|--------------|-------------
claude-opus-4-6                |  0.0 (64.5%) |  0.5 (71.4%) |  0.7 (57.1%) |  0.0 (64.3%) |  0.2 (86.7%) |  0.0 (64.3%) |  0.0 (78.6%)
claude-sonnet-4-5              |  0.5 (48.0%) |  0.5 (50.0%) |  0.0 (57.1%) |  0.0 (64.3%) |  0.0 (60.0%) |  0.0 (60.7%) |  0.0 (64.3%)
codegemma                      |  0.2 (53.3%) |  1.0 (50.0%) |  1.0 (50.0%) |  0.0 (50.0%) |  0.2 (73.3%) |  1.0 (67.9%) |  0.5 (71.4%)
codellama                      |  0.5 (58.6%) |  0.0 (51.8%) |  0.0 (50.0%) |  0.2 (57.1%) |  0.7 (80.0%) |  0.0 (64.3%) |  0.7 (75.0%)
deepseek-coder                 |  0.7 (79.6%) |  1.0 (73.2%) |  0.2 (57.1%) |  0.7 (57.1%) |  0.0 (80.0%) |  0.5 (75.0%) |  0.0 (78.6%)
deepseek-coder_6.7b-instruct   |  0.5 (61.2%) |  1.0 (55.4%) |  0.7 (57.1%) |  0.0 (50.0%) |  0.0 (80.0%) |  0.0 (67.9%) |  1.0 (78.6%)
gemini-2.5-flash               |  0.5 (59.9%) |  1.0 (69.6%) |  0.0 (57.1%) |  0.7 (57.1%) |  0.0 (73.3%) |  0.5 (75.0%) |  1.0 (85.7%)
gpt-3.5-turbo                  |  0.5 (57.9%) |  0.7 (44.6%) |  0.0 (50.0%) |  0.7 (57.1%) |  0.0 (66.7%) |  0.0 (60.7%) |  0.7 (71.4%)
gpt-4                          |  1.0 (50.0%) |  1.0 (58.9%) |  0.7 (50.0%) |  0.2 (53.6%) |  0.5 (73.3%) |  0.7 (67.9%) |  0.5 (75.0%)
gpt-4o                         |  0.2 (49.3%) |  1.0 (50.0%) |  0.7 (50.0%) |  0.0 (50.0%) |  1.0 (66.7%) |  0.2 (60.7%) |  0.5 (71.4%)
gpt-4o-mini                    |  0.0 (49.3%) |  0.7 (50.0%) |  0.0 (46.4%) |  0.0 (50.0%) |  0.0 (66.7%) |  0.2 (46.4%) |  0.7 (67.9%)
gpt-5.2                        |  0.2 (72.4%) |  0.2 (73.2%) |  0.2 (57.1%) |  0.0 (64.3%) |  0.0 (73.3%) |  0.2 (64.3%) |  0.0 (82.1%)
gpt-5.4                        |  1.0 (64.5%) |  0.2 (67.9%) |  0.0 (50.0%) |  0.7 (64.3%) |  0.2 (73.3%) |  0.0 (64.3%) |  0.0 (82.1%)
gpt-5.4-mini                   |  1.0 (60.5%) |  0.7 (64.3%) |  0.0 (57.1%) |  0.0 (57.1%) |  0.0 (73.3%) |  0.0 (64.3%) |  0.0 (85.7%)
llama3.1                       |  0.5 (55.3%) |  1.0 (53.6%) |  0.7 (46.4%) |  0.0 (57.1%) |  0.0 (80.0%) |  0.2 (67.9%) |  0.2 (64.3%)
mistral                        |  0.5 (51.3%) |  1.0 (55.4%) |  0.7 (57.1%) |  0.0 (57.1%) |  0.0 (80.0%) |  0.5 (60.7%) |  1.0 (71.4%)
qwen2.5-coder                  |  1.0 (45.4%) |  0.5 (50.0%) |  0.0 (39.3%) |  0.0 (57.1%) |  1.0 (80.0%) |  0.2 (60.7%) |  0.0 (64.3%)
qwen2.5-coder_14b              |  0.7 (50.0%) |  0.2 (48.2%) |  0.5 (46.4%) |  1.0 (64.3%) |  0.7 (66.7%) |  0.0 (60.7%) |  0.0 (75.0%)
starcoder2                     |  1.0 (78.3%) |  1.0 (76.8%) |  0.7 (57.1%) |  0.0 (57.1%) |  0.5 (73.3%) |  1.0 (71.4%) |  0.2 (78.6%)
```

## Key Insights by Language

### JavaScript: High Creativity Helps (temp 1.0)
- **9/19 models** perform best at temp 1.0
- **Average improvement**: 21.4 pp (Gemini: 48.2% → 69.6%)
- **Why**: Dynamic typing benefits from creative solutions

**Specific Recommendations:**
- **DeepSeek-Coder**: Use temp 1.0 (73.2%) — 16.1 pp better than temp 0.5
- **StarCoder2**: Use temp 1.0 (76.8%) — 12.5 pp better than temp 0.0
- **Gemini 2.5 Flash**: Use temp 1.0 (69.6%) — 21.4 pp better than temp 0.0

### Python: Balanced Approach (temp 0.5)
- **7/19 models** perform best at temp 0.5
- **Average variation**: Only 8.6 pp (most stable language)
- **Why**: Python's explicit syntax benefits from moderate creativity

**Specific Recommendations:**
- **DeepSeek-Coder**: Use temp 0.7 (79.6%) — 10.5 pp variation
- **StarCoder2**: Use temp 1.0 (78.3%) — 16.4 pp variation
- **GPT-5.2**: Use baseline/0.2 (72.4%) — minimal variation

### Java: Deterministic is Best (temp 0.0)
- **8/19 models** perform best at temp 0.0
- **Why**: Type-safe enterprise language prefers precise, deterministic code

**Specific Recommendations:**
- Use temp 0.0 for: Claude Sonnet, CodeLlama, Gemini, GPT-3.5, GPT-4o-mini, GPT-5.4, GPT-5.4-mini, Qwen2.5-Coder
- Use temp 0.7 for: Claude Opus, DeepSeek-Coder 6.7B, GPT-4, GPT-4o, Llama3.1, Mistral, StarCoder2

### C#: Strongly Prefer Deterministic (temp 0.0)
- **12/19 models** perform best at temp 0.0
- **Why**: .NET type system and null safety benefit from precision

**Note**: C# shows the strongest consensus for low temperature across all models.

### C++: Low Temperature for Memory Safety (temp 0.0)
- **10/19 models** perform best at temp 0.0
- **Average score**: 74.0% (second highest after Rust)
- **Why**: Manual memory management requires precise, tested patterns

**Specific Recommendations:**
- **Claude Opus**: Use baseline/0.2 (86.7%) — best C++ score overall
- **DeepSeek-Coder**: Use temp 0.0 (80.0%)
- Most other models: temp 0.0

### Go: Low Temperature for Simplicity (temp 0.0)
- **8/19 models** perform best at temp 0.0
- **Variation**: 11.4 pp average (moderate sensitivity)
- **Why**: Go's simplicity and concurrency patterns prefer deterministic code

**Specific Recommendations:**
- **DeepSeek-Coder**: Use temp 0.5 (75.0%) — 21.4 pp variation!
- **Gemini 2.5 Flash**: Use temp 0.5 (75.0%) — 17.9 pp variation
- **StarCoder2**: Use temp 1.0 (71.4%) — 21.4 pp variation

### Rust: Zero Temperature for Zero Cost (temp 0.0)
- **8/19 models** perform best at temp 0.0
- **Average score**: 74.8% (HIGHEST across all languages)
- **Why**: Borrow checker and ownership require precise, idiomatic patterns

**Specific Recommendations:**
- **GPT-5.4**: Use temp 0.0 (82.1%) — 0.0 pp variation (perfectly stable!)
- **GPT-5.4-mini**: Use temp 0.0 (85.7%) — highest Rust score
- **Gemini 2.5 Flash**: Use temp 1.0 (85.7%) — tied for highest

## Practical Configuration Examples

### Using DeepSeek-Coder

```python
# Configure per language
temperature_settings = {
    'python': 0.7,      # Best: 79.6%
    'javascript': 1.0,  # Best: 73.2%
    'java': 0.2,        # Best: 57.1%
    'csharp': 0.7,      # Best: 57.1%
    'cpp': 0.0,         # Best: 80.0%
    'go': 0.5,          # Best: 75.0%
    'rust': 0.0,        # Best: 78.6%
}
```

### Using StarCoder2

```python
# High temperature for dynamic languages
temperature_settings = {
    'python': 1.0,      # Best: 78.3%
    'javascript': 1.0,  # Best: 76.8%
    'java': 0.7,        # Best: 57.1%
    'csharp': 0.0,      # Best: 57.1%
    'cpp': 0.5,         # Best: 73.3%
    'go': 1.0,          # Best: 71.4%
    'rust': 0.2,        # Best: 78.6%
}
```

### Using GPT-5.4

```python
# Consistent across most languages
temperature_settings = {
    'python': 1.0,      # Best: 64.5%
    'javascript': 0.2,  # Best: 67.9%
    'java': 0.0,        # Best: 50.0%
    'csharp': 0.7,      # Best: 64.3%
    'cpp': 0.2,         # Best: 73.3%
    'go': 0.0,          # Best: 64.3%
    'rust': 0.0,        # Best: 82.1% (perfectly stable!)
}
```

## When to Deviate from Recommendations

**Trust the data, not intuition:**
- Some models contradict general patterns (e.g., GPT-5.4 wants temp 1.0 for Python)
- Language-specific training affects optimal temperature
- Always test your specific model-language combination

**Red flags (test before deploying):**
- Using temp 0.0 for JavaScript with DeepSeek-Coder (loses 14 pp)
- Using temp 1.0 for Java with most models (loses 7-14 pp)
- Using temp 0.7 for Go with DeepSeek-Coder (loses 3.6 pp vs optimal 0.5)

## Average Security Scores by Language

**Language Security Ranking** (higher is better):

1. **Rust**: 74.8% average — Best overall security
2. **C++**: 74.0% average — Strong memory safety patterns
3. **Go**: 64.5% average — Good concurrency safety
4. **JavaScript**: 58.6% average — Higher than Python despite more variation
5. **Python**: 58.4% average — Most stable but not highest scoring
6. **C#**: 57.3% average — Type safety helps
7. **Java**: 52.3% average — Lowest scores (harder for models?)

## Bottom Line

**Temperature is language-specific:**
- JavaScript: Use high temp (1.0) for 9/19 models
- Python: Use medium temp (0.5) for 7/19 models
- All compiled languages: Use low temp (0.0) for majority of models

**The cost of wrong temperature:**
- JavaScript: Up to 21.4 pp loss (Gemini)
- Go: Up to 21.4 pp loss (DeepSeek-Coder, StarCoder2)
- Rust: Up to 21.4 pp loss (DeepSeek-Coder 6.7B)

**Don't use default temperature for all languages** — the data shows optimal settings vary widely by language!
