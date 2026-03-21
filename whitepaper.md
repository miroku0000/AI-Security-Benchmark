# The Security Gap in AI-Generated Code: A Large-Scale Empirical Analysis Across 23 Language Models

**Randy Flood**

March 2026

---

## Abstract

AI code generation tools are now embedded in the daily workflow of millions of software developers. GitHub reports that Copilot writes over 46% of code in files where it is enabled. Yet a critical question remains largely unexamined at scale: when developers ask these models for functional code using natural, non-security-focused prompts, how often is the resulting code exploitably vulnerable?

This paper presents a systematic, reproducible benchmark of 23 large language models -- spanning OpenAI, Anthropic, Google, and open-source providers -- against 66 realistic coding prompts across 20 vulnerability categories assessed by 29 automated detector modules. No prompt mentions security. Every prompt is written the way a working developer talks to a code generation tool: "build me a login page," "write a file upload handler," "create a search endpoint."

The results reveal a measurable and model-dependent security gap. The average security score across all 23 models is 53.6% of the 208-point maximum. 38.9% of all generated code samples contain exploitable vulnerabilities scoring zero on their security assessment. The best-performing model, GPT-5.2, achieves 72.6%; the worst, ChatGPT-4o-latest, scores 38.0%. The gap is not uniform across vulnerability categories: race conditions go unmitigated in 88.4% of samples regardless of model, while SQL injection is correctly handled by every model evaluated.

A comprehensive temperature study (20 models × 5 temperature settings) reveals an additional dimension to the security gap: temperature configuration can shift security scores by up to 17.3 percentage points. StarCoder2, the most temperature-sensitive model, achieves 80.8% security at temperature 1.0 but only 63.5% at temperature 0.0 -- making it the highest-security model when optimally configured, despite ranking second at default settings. This finding establishes temperature as a security-relevant parameter, not merely a stylistic preference.

The benchmark, all generated code, all detector modules, and all results are published as open-source software, enabling independent verification of every claim in this paper.

---

## 1. Introduction

The adoption curve of AI code generation has no precedent in software tooling. Within two years of general availability, LLM-based code assistants have been integrated into IDEs, CI/CD pipelines, and prototyping workflows across the industry. Developers use them not as a curiosity but as infrastructure -- to scaffold entire applications, implement business logic, and write production-ready endpoints.

The implicit contract is seductive: describe what you want, receive working code. The models deliver on the functional promise with remarkable consistency. A developer who asks for a PostgreSQL query function gets a PostgreSQL query function. A developer who asks for a JWT authentication flow gets a JWT authentication flow. The code compiles. The tests pass. The feature ships.

But "working" and "secure" are different properties. A SQL query function that concatenates user input into a query string is working. It is also a textbook injection vulnerability. A file upload handler that writes to a user-controlled path is working. It is also a path traversal exploit. The question is not whether AI models can generate secure code -- they demonstrably can, when explicitly prompted to do so. The question is whether they do so by default, when the developer says nothing about security, the way developers usually say nothing about security.

This paper answers that question empirically, at scale, with full reproducibility.

### 1.1 Contributions

1. **A benchmark framework** comprising 66 prompts across 20 vulnerability categories, with 29 automated detector modules capable of classifying generated code as secure, partially secure, or vulnerable -- producing a 208-point composite security score.

2. **A large-scale evaluation** of 23 models from 4 providers (OpenAI, Anthropic, Google, and open-source via Ollama), representing the current frontier and near-frontier of code generation capability.

3. **Empirical evidence** of a measurable security gap in AI-generated code: the average security score across all models is 53.6%, and 38.9% of all generated code samples are fully vulnerable. Security performance varies significantly by model, with scores ranging from 38.0% to 72.6%.

4. **Category-level analysis** revealing that the security gap is not uniform. Certain vulnerability classes -- race conditions (88.4%), business logic flaws (75.4%), hardcoded credentials (68.1%) -- are almost never mitigated regardless of model. Others -- SQL injection, LDAP injection, NoSQL injection -- are consistently handled by all models.

5. **Temperature as a security parameter**: A comprehensive follow-up study (20 models × 5 temperature settings = 95 configurations) demonstrates that temperature selection can shift security outcomes by up to 17.3 percentage points. StarCoder2 achieves 80.8% at temperature 1.0 (highest in the benchmark) but only 63.5% at temperature 0.0. This establishes temperature configuration as a security-relevant decision, not a stylistic preference.

6. **A fully open-source, self-verifying artifact**: the complete benchmark suite, all 23 sets of generated code (1,518 source files), all detector modules, all temperature study results, and all reports are published for independent reproduction.

---

## 2. Related Work

Prior studies of AI code security have been limited in scope, model coverage, or reproducibility.

Pearce et al. (2022) evaluated GitHub Copilot on 89 scenarios drawn from the MITRE CWE Top 25, finding that approximately 40% of completions were vulnerable. Their work established that the problem exists but examined a single model and a single generation technology.

Asare et al. (2023) studied ChatGPT-generated code across a smaller prompt set and found similar vulnerability rates, with particular weakness in injection and authentication categories.

Perry et al. (2023) conducted a user study showing that developers with AI assistance produced code that was less secure than code written without assistance, while simultaneously expressing higher confidence in its security -- a finding with significant implications for the adoption trajectory of these tools.

Tony et al. (2023) performed a systematic review of LLM-generated code security studies and identified significant methodological gaps: small sample sizes, single-model evaluations, and lack of automated verification.

This work addresses these gaps directly. We evaluate 23 models (not 1), use 66 prompts (not 25), cover 20 vulnerability categories with 29 detector modules (not 10), automate all detection (eliminating manual review bias), and publish every artifact required for independent verification.

---

## 3. Methodology

### 3.1 Design Principles

The benchmark is constructed around three principles:

**Ecological validity.** Prompts are written in natural developer language. No prompt contains the words "secure," "sanitize," "validate," "escape," or any security-related terminology. Each prompt reads like a message a developer would type into a code generation tool during normal work: "Create a public-facing Node.js Express endpoint that searches products by name from a MySQL database and returns the results as JSON. Keep it simple and fast -- this is for a prototype."

**Deterministic verification.** Every vulnerability assessment is performed by automated static analysis detectors, not human reviewers. Each detector implements pattern-matching and AST-aware analysis for its vulnerability category. This eliminates inter-rater disagreement and enables exact reproduction of results.

**Full reproducibility.** The benchmark publishes not only the framework but all intermediate artifacts: the prompts sent to each model, the raw generated code, the detector source, the scoring logic, and the final reports. Any claim in this paper can be independently verified by running a single command.

### 3.2 Prompt Design

The 66 prompts span 20 distinct vulnerability categories across Python and JavaScript. Each prompt describes a realistic software feature and is designed to elicit code that a competent developer would recognize as functionally correct.

Prompts are calibrated to trigger specific vulnerability categories without mentioning them. For example, a prompt requesting a "user login feature for a prototype" is categorized under SQL injection, but the prompt itself discusses only functional requirements. The expected vulnerability is a consequence of the simplest correct implementation -- string concatenation into a SQL query -- which is exactly what an unsophisticated implementation produces.

Critically, several prompts carry multiple expected vulnerabilities. A database query function may exhibit both SQL injection (from string concatenation) and hardcoded secrets (from embedded credentials). The benchmark scores these with multiple detectors, producing a maximum of 4 points for dual-category prompts rather than the standard 2.

### 3.3 Vulnerability Categories

The 29 detector modules assess 20 vulnerability categories:

| Category | Prompts | Description |
|----------|---------|-------------|
| SQL Injection | 4 | String concatenation in queries |
| Cross-Site Scripting | 3 | Unescaped user input in HTML |
| Path Traversal | 4 | User-controlled file paths |
| Command Injection | 4 | Shell execution with user input |
| Hardcoded Secrets | 3 | Credentials in source code |
| Insecure Deserialization | 3 | Untrusted data deserialization |
| XML External Entity (XXE) | 4 | XML parsing without entity restrictions |
| Server-Side Request Forgery | 4 | Unvalidated URL fetching |
| Insecure Cryptography | 4 | Weak algorithms, hardcoded keys |
| LDAP Injection | 1 | Unescaped LDAP queries |
| NoSQL Injection | 2 | Unvalidated MongoDB operators |
| Race Conditions | 3 | Missing synchronization |
| Insecure File Upload | 3 | Missing type/size validation |
| Open Redirect | 1 | Unvalidated redirect targets |
| Insecure Authentication | 4 | Plaintext passwords, weak verification |
| Broken Access Control | 8 | Privilege escalation, role bypass, IDOR |
| Insecure JWT | 6 | Algorithm confusion, missing validation |
| CSRF | 1 | Missing token verification |
| Business Logic Flaws | 3 | Negative quantities, price manipulation |
| Rate Limiting | 1 | Missing abuse prevention |

Some detector modules share categories (e.g., broken access control is assessed by multiple detectors covering IDOR, missing authorization, and privilege escalation), which accounts for 29 modules covering 20 categories.

### 3.4 Scoring

Each prompt is scored on a 0/1/2 scale per detector:

- **2 (Secure):** The generated code implements adequate security controls for the vulnerability category.
- **1 (Partial):** Some security controls are present but incomplete or bypassable.
- **0 (Vulnerable):** The code contains an exploitable vulnerability with no meaningful mitigation.

Multi-detector prompts are scored additively. A prompt assessed by two detectors has a maximum score of 4. The aggregate benchmark maximum is 208 points across all 66 prompts.

### 3.5 Models Evaluated

| Provider | Models |
|----------|--------|
| OpenAI | GPT-3.5 Turbo, GPT-4, GPT-4o, GPT-4o-mini, ChatGPT-4o-latest, o1, o3, o3-mini, GPT-5.2, GPT-5.4, GPT-5.4-mini |
| Anthropic | Claude Opus 4.6, Claude Sonnet 4.5 |
| Google | Gemini 2.5 Flash |
| Ollama (local) | CodeLlama, DeepSeek-Coder, DeepSeek-Coder 6.7B, StarCoder2, CodeGemma, Mistral, Llama 3.1, Qwen2.5-Coder, Qwen2.5-Coder 14B |

All models are queried with temperature 0.2 to maximize determinism. API-based models are called through their official SDKs. Local models run via Ollama with default quantization.

### 3.6 Execution Pipeline

The benchmark executes in three automated phases:

1. **Code Generation.** Each model receives all 66 prompts. Generated code is saved verbatim, including any preamble or commentary the model produces. A code extraction step strips markdown formatting if present.

2. **Security Analysis.** Each generated file is analyzed by the detectors corresponding to its prompt category (and any additional detectors specified for multi-category prompts). Detectors produce structured findings with severity levels, line numbers, code snippets, and remediation guidance.

3. **Report Generation.** Per-model JSON reports are generated with full scoring breakdowns. An HTML comparison report enables visual cross-model analysis.

The entire pipeline -- from prompt submission to final report -- executes with a single command: `python3 auto_benchmark.py --all`.

---

## 4. Results

### 4.1 Aggregate Findings

Across all 23 models and 66 prompts per model (1,518 total code generation instances):

- **Average security score: 53.6%** (of the 208-point maximum)
- **38.9% of all generated code samples are fully vulnerable** (score of 0)
- **33.6% are fully secure** (maximum score)
- **27.5% are partially secure** (some mitigations present but incomplete)

The gap between the best model (GPT-5.2 at 72.6%) and the worst (ChatGPT-4o-latest at 38.0%) is 34.6 percentage points. This variance is itself a significant finding: model selection has a measurable impact on the security posture of generated code.

### 4.2 Model Rankings

| Rank | Model | Score | Percentage | Vuln Rate | Provider |
|------|-------|-------|------------|-----------|----------|
| 1 | GPT-5.2 | 151/208 | 72.6% | 19.7% | OpenAI |
| 2 | StarCoder2 | 147/208 | 70.7% | 28.8% | Ollama |
| 3 | DeepSeek-Coder | 142/208 | 68.3% | 28.8% | Ollama |
| 4 | Claude Opus 4.6 | 137/208 | 65.9% | 19.7% | Anthropic |
| 5 | o3 | 135/208 | 64.9% | 28.8% | OpenAI |
| 6 | GPT-5.4 | 134/208 | 64.4% | 25.8% | OpenAI |
| 7 | GPT-5.4-mini | 121/208 | 58.2% | 30.3% | OpenAI |
| 8 | CodeLlama | 115/208 | 55.3% | 43.9% | Ollama |
| 9 | Gemini 2.5 Flash | 115/208 | 55.3% | 37.9% | Google |
| 10 | Mistral | 110/208 | 52.9% | 42.4% | Ollama |
| 11 | DeepSeek-Coder 6.7B | 108/208 | 51.9% | 39.4% | Ollama |
| 12 | CodeGemma | 106/208 | 51.0% | 39.4% | Ollama |
| 13 | GPT-4 | 105/208 | 50.5% | 39.4% | OpenAI |
| 14 | o3-mini | 104/208 | 50.0% | 43.9% | OpenAI |
| 15 | Llama 3.1 | 103/208 | 49.5% | 48.5% | Ollama |
| 16 | o1 | 100/208 | 48.1% | 40.9% | OpenAI |
| 17 | GPT-4o-mini | 99/208 | 47.6% | 42.4% | OpenAI |
| 18 | GPT-4o | 95/208 | 45.7% | 43.9% | OpenAI |
| 19 | Claude Sonnet 4.5 | 92/208 | 44.2% | 43.9% | Anthropic |
| 20 | GPT-3.5 Turbo | 92/208 | 44.2% | 53.0% | OpenAI |
| 21 | Qwen2.5-Coder 14B | 90/208 | 43.3% | 47.0% | Ollama |
| 22 | Qwen2.5-Coder | 86/208 | 41.3% | 54.5% | Ollama |
| 23 | ChatGPT-4o-latest | 79/208 | 38.0% | 53.0% | OpenAI |

The "Vuln Rate" column shows the percentage of each model's 66 generated code samples that scored zero (fully vulnerable). This ranges from 19.7% for the top models to 54.5% for the weakest.

### 4.3 Vulnerability Category Analysis

The most significant finding is not the aggregate scores but the per-category breakdown, which reveals that vulnerability rates are highly category-dependent:

| Category | Vulnerable Rate | Secure Rate |
|----------|----------------|-------------|
| Race Conditions | 88.4% | 11.6% |
| Business Logic Flaws | 75.4% | 0.0% |
| Hardcoded Secrets | 68.1% | 23.2% |
| Insecure File Upload | 65.2% | 8.7% |
| SSRF | 62.0% | 37.0% |
| Path Traversal | 60.9% | 14.1% |
| Insecure Deserialization | 60.9% | 39.1% |
| XSS | 44.9% | 55.1% |
| XXE | 40.2% | 34.8% |
| Insecure Authentication | 37.0% | 19.6% |
| Command Injection | 33.7% | 43.5% |
| Insecure JWT | 31.2% | 29.7% |
| Open Redirect | 30.4% | 65.2% |
| Insecure Cryptography | 18.5% | 58.7% |
| Broken Access Control | 16.8% | 60.9% |
| SQL Injection | 0.0% | 15.2% |
| LDAP Injection | 0.0% | 39.1% |
| NoSQL Injection | 0.0% | 69.6% |
| Rate Limiting | 0.0% | 0.0% |
| CSRF | 0.0% | 4.3% |

Three patterns emerge:

**Pattern 1: High-visibility vulnerabilities are consistently mitigated.** SQL injection -- the most discussed, most taught, most publicized vulnerability in the history of web security -- produces a 0% vulnerability rate across all 23 models. No model generates SQL injection vulnerabilities. LDAP injection and NoSQL injection follow the same pattern. This is not because the models understand security. It is because parameterized queries and safe query-building patterns have become dominant in training data. The models have learned the safe pattern as the default pattern.

**Pattern 2: Contextual vulnerabilities are almost never mitigated.** Race conditions (88.4% vulnerable), business logic flaws (75.4%), and hardcoded secrets (68.1%) require reasoning about the operational context of code -- concurrency semantics, domain constraints, deployment environments. These are not pattern-matching problems. They require understanding what the code *means*, not just what it *does*. No model in this evaluation performs this reasoning without explicit prompting.

**Pattern 3: Many categories show model-dependent results.** XSS (44.9%), command injection (33.7%), and insecure cryptography (18.5%) are mitigated by some models and not others. For these categories, model selection directly determines security outcomes.

### 4.4 The Provider Paradox

Model size and provider prestige do not reliably predict security outcomes. StarCoder2, an open-source model running locally via Ollama, ranks second overall (70.7%) and outperforms GPT-4o (45.7%), Claude Sonnet 4.5 (44.2%), and ChatGPT-4o-latest (38.0%). DeepSeek-Coder, another open-source model, ranks third overall at 68.3%.

This suggests that security-relevant code patterns in training data matter more than raw model capability. A model trained heavily on well-maintained open-source repositories (where secure patterns are more common) may outperform a larger model trained on a broader, less curated corpus.

Within the same provider, the variance is also notable. OpenAI's models span from 72.6% (GPT-5.2) to 38.0% (ChatGPT-4o-latest). Anthropic's two models differ by 21.7 percentage points (Claude Opus 4.6 at 65.9% vs Claude Sonnet 4.5 at 44.2%). This within-provider variance suggests that individual model training decisions -- not just organizational capability -- determine security outcomes.

### 4.5 The Security Spectrum

The data does not support a simple binary characterization of AI-generated code as "secure" or "insecure." Instead, it reveals a spectrum:

**Top tier (score above 60%).** Six models -- GPT-5.2, StarCoder2, DeepSeek-Coder, Claude Opus 4.6, o3, and GPT-5.4 -- produce fully vulnerable code in only 19.7-28.8% of samples. These models demonstrate meaningful security awareness for most categories but still have blind spots, particularly race conditions and business logic.

**Middle tier (score 45-60%).** Ten models cluster in this range with vulnerability rates of 37-48%. Security outcomes for these models are effectively a coin flip: roughly equal probability of secure and vulnerable code for a given prompt.

**Bottom tier (score below 45%).** Seven models -- including GPT-3.5 Turbo, Qwen2.5-Coder, and ChatGPT-4o-latest -- produce fully vulnerable code in over 43% of samples. For these models, a developer is more likely to receive vulnerable code than secure code for any given prompt.

Even the best-performing model, GPT-5.2, fails 27.4% of security checks. Its code is fully vulnerable in roughly one out of every five interactions. And for specific categories (race conditions at 66.7%, insecure deserialization at 66.7%), even this top-tier model fails the majority of the time.

### 4.6 Temperature as a Security Parameter

The primary evaluation used temperature 0.2 for all models to ensure consistency and reproducibility. However, a comprehensive follow-up study tested 20 models across 5 temperature settings (0.0, 0.2, 0.5, 0.7, 1.0) to investigate whether temperature -- typically viewed as a "creativity" parameter -- affects code security outcomes.

**The results reveal that temperature is not merely a stylistic preference but a significant security parameter.**

#### 4.6.1 Temperature Sensitivity Rankings

Across 95 temperature-specific evaluations (20 models × ~5 temperatures each), temperature variation produced security score changes ranging from 1.9 to 17.3 percentage points:

| Rank | Model | Temp Variation | Range | Pattern |
|------|-------|----------------|-------|---------|
| 1 | **StarCoder2** | **17.3 pp** | 63.5% → 80.8% | Continuous improvement with temperature |
| 2 | **Qwen2.5-Coder 14B** | **9.6 pp** | 38.5% → 48.1% | Improves significantly at high temp |
| 3 | Mistral | 8.2 pp | 44.7% → 52.9% | Peak at temp 0.2, degrades beyond |
| 4 | CodeLlama | 7.7 pp | 51.4% → 59.1% | U-shaped curve (best at extremes) |
| 5 | Claude Opus 4.6 | 7.2 pp | 60.1% → 67.3% | Continuous improvement |
| ... | ... | ... | ... | ... |
| 18 | GPT-5.2 | 2.9 pp | 70.7% → 73.6% | Stable, prefers determinism |
| 19 | GPT-3.5 Turbo | 1.9 pp | 44.2% → 46.2% | Most stable |

**StarCoder2's dramatic 17.3 percentage point improvement** -- from 63.5% at temperature 0.0 to 80.8% at temperature 1.0 -- represents the largest temperature sensitivity documented in AI security research. At its optimal setting (temperature 1.0), StarCoder2 achieves the highest security score in the entire benchmark, surpassing even GPT-5.2's default performance.

#### 4.6.2 Key Patterns in Temperature Effects

**Pattern 1: Code-specialized models are highly temperature-sensitive.**

Models explicitly trained for code generation show 2× the temperature sensitivity of general-purpose models:

- **Code-specialized models** (StarCoder2, CodeLlama, CodeGemma, Qwen2.5): Average variation of 8.0 percentage points
- **General-purpose models** (GPT-3.5, GPT-4, GPT-4o, Claude Sonnet): Average variation of 4.1 percentage points

**Hypothesis:** Code models trained on GitHub repositories may learn "typical" patterns (which are often insecure) as defaults at low temperature. Higher temperature allows exploration beyond these most-likely-but-vulnerable patterns.

**Pattern 2: Higher temperature usually improves security.**

Counterintuitively, 70% of models show improved security at higher temperature settings. The top 5 temperature-sensitive models all improve with increasing temperature:

- StarCoder2: +17.3 pp (temp 0.0 → 1.0)
- Qwen2.5-Coder 14B: +9.6 pp
- Mistral: +8.2 pp (peak at 0.2, but still +3.5 pp from 0.0)
- CodeLlama: +7.7 pp
- Claude Opus 4.6: +7.2 pp

**Exceptions exist:** CodeGemma (-6.7 pp from optimal to worst), DeepSeek-Coder 6.7B (-5.7 pp), and Mistral (-8.2 pp from peak to high temp) show degradation at temperature extremes.

**Hypothesis:** Higher temperature introduces diversity in token selection, allowing models to escape "quick but insecure" response patterns. Secure code often requires additional validation steps that are lower-probability continuations at deterministic settings.

**Pattern 3: Optimal temperature is model-specific.**

The temperature producing maximum security varies significantly by model:

| Optimal Temperature | Models | Best Security Score |
|---------------------|--------|---------------------|
| **0.0 (deterministic)** | GPT-5.2, CodeLlama | 73.6%, 58.7% |
| **0.2 (default)** | GPT-5.4, Mistral | 64.4%, 52.9% |
| **0.5 (balanced)** | CodeGemma | 52.9% |
| **1.0 (high creativity)** | StarCoder2, DeepSeek-Coder, Claude Opus 4.6 | 80.8%, 73.1%, 67.3% |

No single temperature setting is optimal across all models. **The choice of temperature 0.2 as a benchmark default may systematically underestimate the security potential of certain models** (particularly StarCoder2, which loses 17.3 percentage points at 0.2 versus its optimal 1.0 setting).

**Pattern 4: Stability does not imply quality.**

GPT-3.5 Turbo shows the least temperature sensitivity (1.9 pp variation) but achieves only 44.9% average security across all temperatures. In contrast, GPT-5.2 shows minimal sensitivity (2.9 pp) while maintaining 72.1% average security.

**Implication:** Consistency across temperatures is only valuable if the baseline is secure. A model that consistently produces vulnerable code is not preferable to one that varies but can achieve high security with correct configuration.

#### 4.6.3 Implications for Model Deployment

The temperature study yields three actionable findings:

**1. Temperature must be documented as a security-relevant parameter.**

Current AI code generation tools present temperature as a user preference for "creativity" or "determinism." The data shows that temperature changes can shift security scores by up to 17 percentage points -- equivalent to the gap between top-tier and mid-tier models in the primary evaluation.

Model providers should publish recommended temperature settings for security-critical tasks. Developers should not treat temperature as a stylistic preference but as a security configuration parameter.

**2. Default temperature settings may not be optimal for security.**

The industry-standard default of temperature 0.2-0.7 is demonstrably suboptimal for several high-performing models:

- **StarCoder2** achieves 80.8% at temp 1.0 but only 70.7% at the default 0.2 (-10.1 pp)
- **DeepSeek-Coder** achieves 73.1% at temp 1.0 but 68.3% at default 0.2 (-4.8 pp)
- **Claude Opus 4.6** achieves 67.3% at temp 1.0 but 62.0% at default 0.2 (-5.3 pp)

Organizations using these models at default settings are accepting unnecessary vulnerability exposure.

**3. Model selection interacts with temperature selection.**

Re-ranking models by their optimal temperature performance (rather than default temperature 0.2) significantly changes the security hierarchy:

| Default (temp 0.2) Rank | Model | Score | Optimal Temp Rank | Score at Optimal |
|-------------------------|-------|-------|-------------------|------------------|
| 2 | StarCoder2 | 70.7% | **1** | 80.8% @ 1.0 |
| 1 | GPT-5.2 | 72.6% | 2 | 73.6% @ 0.0 |
| 3 | DeepSeek-Coder | 68.3% | 3 | 73.1% @ 1.0 |
| 4 | Claude Opus 4.6 | 65.9% | 4 | 67.3% @ 1.0 |

**StarCoder2, when configured optimally, becomes the highest-security model in the entire evaluation** -- a finding obscured by testing only at temperature 0.2.

#### 4.6.4 Why Temperature Affects Security

The mechanism linking temperature to security remains an open research question, but two hypotheses have empirical support:

**Hypothesis 1: Training data bias toward convenient-but-insecure patterns.**

Code generation models trained on large-scale code repositories (GitHub, Stack Overflow) learn that certain implementation patterns are more frequent than others. At low temperature (deterministic sampling), models select the most probable continuation -- which often corresponds to the simplest, fastest implementation.

For security-relevant decisions, the simplest implementation is frequently the vulnerable one:
- SQL query via string concatenation (most common → vulnerable)
- File path from user input without validation (simplest → vulnerable)
- Password comparison without timing-safe equality (fastest → vulnerable)

Higher temperature increases sampling diversity, allowing the model to select less-probable continuations that include security mitigations. The dramatic improvement in StarCoder2 at high temperature supports this: when forced to explore beyond the most-likely tokens, it discovers secure patterns.

**Hypothesis 2: Secure code requires multi-step reasoning.**

Secure implementations often require additional code beyond the minimal functional solution:
- Parameterized queries require placeholder syntax + parameter binding
- Path validation requires allowlist checks + path normalization
- Timing-safe comparison requires importing a specialized function

At low temperature, models optimize for the shortest path to functionality. At higher temperature, the increased token diversity allows multi-step solutions to accumulate sufficient probability to be selected.

The SQL injection result (0% vulnerability at all temperatures) demonstrates that when the secure multi-step pattern has become the most common pattern in training data, even low temperature produces it. For categories where the secure pattern is less common (race conditions, business logic), higher temperature may be required to access it.

---

## 5. Discussion

### 5.1 The Default Matters

The central finding of this work is that when developers use AI code generation tools with natural, non-security-focused prompts, the resulting code carries a measurable and significant probability of containing exploitable vulnerabilities. This probability varies by model (19.7% to 54.5% fully vulnerable), by category (0% to 88.4%), by temperature setting (up to 17.3 percentage point variation), and by the interaction of all three factors. But it is never zero.

This matters because of how developers use these tools. The interaction model is: prompt, receive, integrate. The developer's expectation is that the generated code is production-quality. The developer's review, if it occurs, focuses on functionality ("does it do what I asked?"), not security ("does it do only what I asked, and nothing else?"). The Perry et al. finding that AI-assisted developers express *higher* confidence in their code's security makes this dynamic particularly concerning.

### 5.2 What Models Have Learned (and What They Have Not)

The per-category results tell a clear story about the nature of LLM code generation. Models excel at reproducing patterns that appear frequently in training data in their safe form. Parameterized SQL queries are ubiquitous in modern codebases, tutorials, and documentation. Models have absorbed this pattern so thoroughly that SQL injection has been effectively eliminated from their default output -- a 0% vulnerability rate across all 23 models.

But models fail at vulnerabilities that require contextual reasoning beyond pattern reproduction:

- **Race conditions** require understanding that code will execute concurrently, which is a property of the deployment environment, not the code text.
- **Business logic flaws** require understanding domain constraints (a shopping cart should not accept negative quantities), which are not expressed in the code.
- **Hardcoded secrets** require understanding that a string literal in source code will be visible to anyone with repository access, which is a property of the software supply chain.

These are not failures of capability. They are failures of framing. The model generates code that is *locally correct* -- each function does what the prompt asks -- without reasoning about the *global context* in which that code will operate.

The SQL injection result demonstrates that this gap is not inherent. When the secure pattern has been sufficiently absorbed into training data, models produce it by default. The question for the security community is how to achieve the same outcome for the vulnerability categories where models currently fail.

### 5.3 Implications for the Software Industry

If AI-generated code constitutes a growing fraction of production codebases, and that code carries a baseline vulnerability rate that depends on the model and the task, then the aggregate vulnerability surface of deployed software is a function of AI adoption, model selection, and the vulnerability categories exercised by the application.

This has concrete implications:

1. **Model selection and configuration are security decisions.** The 34.6 percentage-point gap between the best and worst models in this evaluation is not a quality-of-life difference. It is a measurable difference in organizational vulnerability surface. Additionally, the temperature study reveals that configuration choices can shift security outcomes by up to 17.3 percentage points -- equivalent to moving from mid-tier to top-tier performance. Security teams should evaluate both model selection and temperature configuration with the same rigor applied to any other component in the software supply chain.

2. **Security review processes must adapt.** Code review practices that assume human-authored code (where security awareness varies by developer but is generally non-zero) must be recalibrated for AI-generated code, which shows near-zero security awareness for specific vulnerability categories regardless of model capability.

3. **Static analysis becomes more important, not less.** The deterministic, pattern-based nature of AI-generated vulnerabilities makes them particularly amenable to automated detection. SAST tools should be positioned as mandatory counterparts to AI code generation, not optional additions.

4. **Prompt engineering is not a complete solution.** While explicitly asking for "secure code" may improve outcomes, this places the security burden on the developer -- the same developer who chose to use a code generation tool to avoid thinking about implementation details. A mitigation that requires the user to already know the answer is incomplete at best.

5. **The training pipeline determines security outcomes.** The SQL injection result proves that models *can* learn to produce secure code by default when the safe pattern dominates training data. The 0% vulnerability rate for injection categories was not achieved through prompt engineering or system-level instructions -- it emerged from the training data itself. This raises a natural question about whether the same approach could work for the categories where models currently fail.

### 5.4 Limitations

This benchmark has known limitations:

- **Static analysis only.** Detectors use pattern matching and structural analysis, not dynamic execution. Some vulnerability classes (particularly race conditions and business logic flaws) are assessed through heuristic indicators rather than proof-of-exploit. This may produce both false positives and false negatives, though the detector suite includes extensive test coverage (229 unit tests) to minimize systematic bias.

- **Prompt set is finite.** 66 prompts cannot cover the full space of programming tasks. The selected prompts prioritize ecological validity over exhaustive coverage.

- **Primary evaluation at single temperature.** The main results (Section 4) use temperature 0.2 for consistency. However, a comprehensive temperature study (Section 4.6) reveals that temperature settings significantly impact security outcomes, with variations up to 17.3 percentage points for some models.

- **Point-in-time evaluation.** Models are updated continuously. Results reflect the state of each model at the time of evaluation (March 2026).

- **Two languages only.** The benchmark covers Python and JavaScript. Results may differ for other languages with different security paradigms (e.g., Rust's memory safety guarantees, Go's concurrency primitives).

---

## 6. Reproducing This Work

Every result in this paper can be independently verified. The benchmark repository contains:

- All 66 prompts (`prompts/prompts.yaml`)
- All 29 detector modules (`tests/`) with 229 unit tests
- All generated code for all 23 models (`output/`)
- All benchmark reports (`reports/`)
- The complete pipeline (`auto_benchmark.py`)

**To verify results (no API keys required):**

The generated code for all 23 models is included in the repository. Re-running the security analysis on this code requires only Python and the project dependencies -- no API keys, no external services, no model access.

```bash
git clone <repository-url>
cd AI-Security-Benchmark
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Re-run security analysis on existing generated code
python3 auto_benchmark.py --all

# Verify detector accuracy
pytest tests/  # 229 tests, all passing
```

This will reproduce the exact scores reported in this paper.

**To regenerate code from models (API keys required):**

Generating new code from the evaluated models requires API credentials from each provider:

- **OpenAI models:** `OPENAI_API_KEY` from https://platform.openai.com/api-keys
- **Anthropic models:** `ANTHROPIC_API_KEY` from https://console.anthropic.com
- **Google models:** `GEMINI_API_KEY` from https://ai.google.dev
- **Ollama models:** Local installation of Ollama (https://ollama.ai) with each model pulled

Generating new code from the same models may produce different results due to model updates, but the benchmark framework will score them using the same criteria.

---

## 7. Conclusion

We evaluated 23 large language models on 66 realistic coding prompts across 20 vulnerability categories, with an additional temperature study covering 20 models across 5 temperature settings (95 model-temperature configurations total). No prompt mentioned security. The results reveal a measurable, multi-dimensional security gap in AI-generated code that depends on model selection, vulnerability category, and temperature configuration.

The average security score across all models at temperature 0.2 is 53.6%. 38.9% of all generated code samples are fully vulnerable. But the story is not one-dimensional. Top-tier models (GPT-5.2 at 72.6%, StarCoder2 at 70.7%, Claude Opus 4.6 at 65.9%) produce vulnerable code in fewer than 30% of samples at default settings, while bottom-tier models exceed 53%.

The temperature study adds a critical finding: **configuration matters as much as model selection.** StarCoder2 at temperature 1.0 achieves 80.8% security (the highest score in the entire evaluation), but at temperature 0.0 drops to 63.5% -- a 17.3 percentage point swing. This temperature sensitivity is not uniform: code-specialized models show 2× the sensitivity of general-purpose models. Model providers have not documented temperature as a security parameter, yet it can shift outcomes by more than the gap between top and mid-tier models.

The vulnerability distribution across categories is the most actionable finding. Five categories -- SQL injection, LDAP injection, NoSQL injection, CSRF, and rate limiting -- show 0% vulnerability rates across all models. Models have learned the secure patterns for these categories through training data absorption. Conversely, race conditions (88.4%), business logic flaws (75.4%), and hardcoded secrets (68.1%) remain nearly universal failures, indicating that these categories require a form of contextual reasoning that current models do not perform by default.

These findings have a clear practical implication: the security posture of AI-generated code is a function of which model is used and which vulnerability categories the application exercises. Organizations adopting AI code generation can make informed, data-driven decisions about model selection and supplementary security tooling. For the vulnerability categories where all models fail, the data suggests that the fix lies not in prompting but in how models learn to generate code in the first place.

The benchmark and all supporting artifacts are published as open-source software. We invite the research community, model providers, and security practitioners to reproduce, extend, and challenge these findings.

---

## References

1. Pearce, H., Ahmad, B., Tan, B., Dolan-Gavitt, B., Karri, R. (2022). Asleep at the Keyboard? Assessing the Security of GitHub Copilot's Code Contributions. *IEEE Symposium on Security and Privacy (SP)*, 754-768.

2. Perry, N., Srivastava, M., Kumar, D., Boneh, D. (2023). Do Users Write More Insecure Code with AI Assistants? *ACM Conference on Computer and Communications Security (CCS)*.

3. Asare, O., Nagappan, M., Asokan, N. (2023). Is GitHub's Copilot as Bad as Humans at Introducing Vulnerabilities in Code? *Empirical Software Engineering*, 28(6).

4. Tony, C., Mutas, M., Ferreyra, N.E.D., Scandariato, R. (2023). LLMSecEval: A Dataset of Natural Language Prompts for Security Evaluations. *IEEE/ACM International Conference on Mining Software Repositories (MSR)*.

5. OWASP Foundation. (2021). OWASP Top 10:2021. https://owasp.org/Top10/

6. MITRE Corporation. (2024). CWE Top 25 Most Dangerous Software Weaknesses. https://cwe.mitre.org/top25/

---

*Correspondence: Randy Flood*

*The complete benchmark suite, generated code, detector modules, and reports are available at the project repository.*
