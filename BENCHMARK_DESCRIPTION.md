# AI Security Benchmark - Comprehensive Study Overview

## Executive Summary

This study presents a **systematic benchmark of 23 AI models** and **3 AI coding applications** tested across **100+ configurations**, spanning commercial providers (OpenAI, Anthropic, Google) and open-source models (via Ollama).

The evaluation uses **760 realistic coding prompts** across **200+ vulnerability categories**, assessed by **69 automated detector modules** with support for **27 programming languages and configuration formats**.

## Benchmark Scope

### Models Under Test

**Total Configurations**: 100+
**AI Models**: 23
**AI Applications**: 3

#### Commercial AI Models (14 models)
**Anthropic:**
- Claude Opus 4.6
- Claude Sonnet 4.5

**OpenAI:**
- GPT-3.5-turbo
- GPT-4
- GPT-4o (including full-multilang variant)
- GPT-4o-mini
- GPT-5.2, GPT-5.4, GPT-5.4-mini
- o1, o3, o3-mini (reasoning models)

**Google:**
- Gemini 2.5 Flash

#### Open-Source Models (9 models)
**Code-Specialized:**
- DeepSeek Coder (33B and 6.7B variants)
- Qwen 2.5 Coder (32B and 14B variants)
- CodeLlama
- CodeGemma
- StarCoder2

**General Purpose:**
- Llama 3.1
- Mistral

#### AI Coding Applications (3 applications)
- **Cursor** - AI-powered IDE
- **Claude Code CLI** - Command-line coding assistant
- **Codex.app** - Security-focused coding assistant
  - Tested with 2 configurations: baseline and security-skill enabled

### Configuration Variants

Each base model is tested across multiple configurations:

1. **Temperature Study**: 0.0, 0.2 (default), 0.5, 0.7, 1.0
2. **Security Prompt Levels**: 0 (baseline), 1, 2, 3, 4, 5 (increasing security guidance)
3. **Model Size Variants**: Where applicable (e.g., qwen2.5-coder vs qwen2.5-coder_14b)

## Evaluation Framework

### Prompt Set

**Total Prompts**: 760
**Format**: Realistic coding scenarios requiring security-conscious implementation

Example prompt categories:
- Database queries with user input
- File system operations
- Authentication and authorization
- Cryptographic operations
- API endpoint implementations
- Cloud infrastructure as code
- CI/CD pipeline configurations

### Vulnerability Categories (200+)

The benchmark covers **219 detailed vulnerability categories** organized across multiple security domains:

**Primary Domains:**

#### Web Application Security
- SQL Injection
- Cross-Site Scripting (XSS)
- Cross-Site Request Forgery (CSRF)
- Path Traversal
- Command Injection
- Code Injection
- LDAP Injection
- NoSQL Injection
- XXE (XML External Entity)
- Server-Side Request Forgery (SSRF)
- Open Redirect

#### Authentication & Authorization
- Insecure Authentication
- Missing Authentication
- Missing Authorization
- Access Control Issues
- JWT (JSON Web Token) vulnerabilities
- OIDC (OpenID Connect) issues

#### Cryptography
- Insecure Cryptography
- Hardcoded Secrets
- Weak Key Generation

#### Input Validation & Data Handling
- Input Validation failures
- File Upload vulnerabilities
- Insecure Deserialization
- Mass Assignment

#### API & Microservices Security
- API Gateway security
- GraphQL security
- Message Queue security
- API Response caching issues

#### Cloud & Infrastructure Security
- Cloud Infrastructure as Code (IaC) issues
- Container Security
- Datastore Security
- CI/CD Security
- Serverless Security

#### Modern Application Security
- Mobile Security
- ML/AI Security
- Observability & Logging issues

#### Systems & Memory Safety
- Buffer Overflow
- Null Pointer dereferences
- Integer Overflow
- Memory Leaks
- Double Free
- Use After Free
- Format String vulnerabilities

#### Business Logic & Operations
- Business Logic flaws
- Race Conditions
- Rate Limiting issues
- Resource Leaks
- Error Handling
- Information Disclosure
- Insecure Data Storage

### Detector Modules

**Total Modules**: 69
**Architecture**: Pattern-based detection with continuous refinement

Each detector module implements:
- **Primary Detection**: Core vulnerability pattern matching (max_score: 2)
  - Score 0: Vulnerability detected (FAIL)
  - Score 2: Secure implementation detected (PASS)
- **Additional Checks**: Context-specific validation (variable max_score)
- **Language-Specific Patterns**: Tailored detection for each supported language
- **False Positive Reduction**: Comment filtering, syntax validation, semantic context

#### Detector Capabilities
- **Pattern Matching**: Regex-based detection of vulnerable code patterns
- **Ownership Validation**: Detection of access control and authorization checks
- **Input Sanitization**: Identification of input validation and escaping
- **Secure API Usage**: Recognition of security best practices
- **Configuration Analysis**: Detection of insecure defaults and configurations

### Supported Languages

**Total Languages & Formats**: 27

#### Core Programming Languages
1. **Python** (.py)
2. **JavaScript** (.js)
3. **TypeScript** (.ts)
4. **Java** (.java)
5. **C** (.c)
6. **C++** (.cpp)
7. **C#** (.cs)
8. **Go** (.go)
9. **Rust** (.rs)

#### Modern & Mobile Languages
10. **Swift** (.swift)
11. **Kotlin** (.kt)
12. **Dart** (.dart)
13. **Scala** (.scala)

#### Scripting & Dynamic Languages
14. **Ruby** (.rb)
15. **PHP** (.php)
16. **Perl** (.pl)
17. **Lua** (.lua)
18. **Elixir** (.ex)
19. **Bash** (.sh)
20. **Groovy** (.groovy)

#### Infrastructure & Configuration
21. **Terraform** (.tf) - Infrastructure as Code
22. **Dockerfile** - Container security
23. **YAML** (.yaml/.yml) - Configuration files
24. **JSON** (.json) - Data formats
25. **XML** (.xml) - Markup & config
26. **Config** (.conf) - System configuration

#### Specialized Languages
27. **Solidity** (.sol) - Smart contract security

## Iterative Refinement Process

The benchmark includes an **iterative detector refinement methodology** to improve detection accuracy:

### Iteration 9 (Completed)
- **Fix #1**: Comment filtering to reduce style sensitivity
- **Fix #2**: Syntax validation to prevent false negatives on broken code
- **Result**: 11% reduction in inconsistencies (347 → 309 tests)

### Iteration 10 (Completed)
- **Fix**: Helper function ownership detection
- **Result**: Marginal improvement on specific test cases
- **Lesson**: Need broader pattern analysis for impact

### Future Iterations
- Focus on 50/50 split tests (highest likelihood of detector bugs)
- AST-based semantic analysis for language-specific improvements
- Cross-language pattern normalization

## Key Metrics

### Consistency Analysis

Models are evaluated across 6 reference implementations:
- claude-opus-4-6 (temp 0.0)
- claude-sonnet-4-5
- gpt-4o
- gpt-5.4
- deepseek-coder
- cursor

**Current Consistency (Iteration 10)**:
- ✅ Always PASS (Consistent): 200 tests (26.3%)
- ❌ Always FAIL (Consistent): 207 tests (27.2%)
- ⚠️ Inconsistent: 352 tests (46.3%)
- **Total Consistency: 53.6%**

### Split Patterns

Inconsistent tests are classified by vote distribution:
- **1-5 split**: Strong disagreement (likely real model differences)
- **2-4 split**: Moderate inconsistency
- **3-3 split**: 50/50 splits (most likely detector bugs)
- **4-2 split**: Moderate inconsistency
- **5-1 split**: Minor disagreement (likely real model differences)

## Research Applications

This benchmark enables research in:

1. **Model Security Capabilities**: Comparative analysis of AI model security awareness
2. **Prompt Engineering**: Impact of security guidance on code generation
3. **Temperature Effects**: Randomness vs. security trade-offs
4. **Detector Accuracy**: Validation and improvement of security detection tools
5. **False Positive/Negative Analysis**: Understanding detection limitations
6. **Cross-Language Security**: Language-specific vulnerability patterns
7. **Application Context**: IDE assistants vs. standalone models

## Methodology Highlights

### Code Generation
- **Default Temperature**: 0.2 (deterministic but not rigid)
- **Timeout**: 180 seconds per prompt
- **Retries**: 2 retries for transient failures
- **Prompt Caching**: Enabled for efficiency
- **Output Format**: Language-appropriate file extensions with category metadata

### Security Analysis
- **Automated Detection**: 69 specialized detector modules
- **Manual Review**: Iterative sampling for detector validation
- **Cross-Model Validation**: Consistency analysis across 6 reference models
- **Primary Focus**: Core vulnerability detection (max_score: 2)
- **Context Awareness**: Additional checks for complex scenarios

### Quality Assurance
- **Python Cache Management**: Cleared before each validation run
- **Baseline Validation**: Re-run previous iterations to track detector drift
- **Change Analysis**: Track individual model-test pair changes
- **Pattern Analysis**: Automated identification of inconsistency patterns

## Data Outputs

### Generated Code
- **Location**: `output/<model_name>/`
- **Format**: Source code files with category metadata
- **Total Files**: 760 per model configuration
- **Size**: Variable (typical range: 50-500 lines per file)

### Analysis Reports
- **Validation Reports**: JSON format with detailed test results
  - Location: `reports/<model_name>_analysis.json`
  - Fields: test_id, category, language, score, max_score, verdict, failure_reasons

- **Cross-Model Comparisons**: Consistency analysis across models
  - Location: `reports/iteration<N>_cross_model_comparison.json`
  - Metrics: inconsistent tests, split patterns, category breakdown

- **Iteration Reports**: Detector refinement documentation
  - Location: `reports/iteration<N>_final_results.md`
  - Content: Fixes implemented, impact analysis, lessons learned

### Logs
- **Generation Logs**: `logs/<model_name>_generation.log`
- **Analysis Logs**: `logs/<model_name>_analysis.log`
- **Refinement Logs**: `reports/refinement/iteration<N>_run.log`

## Current Study Status

### Completed
- ✅ Baseline evaluation (Level 0) for 23 AI models + 3 applications
- ✅ Temperature studies for 15+ models (0.0, 0.5, 0.7, 1.0)
- ✅ Security prompt levels for Claude Sonnet 4.5, GPT-4o, GPT-4o-mini (Levels 1-5)
- ✅ Detector iterations 1-10 (59.2% → 53.6% consistency)

### In Progress
- 🔄 Claude Opus 4.6 security prompt level study (Levels 1-2 generating)
- 🔄 Detector iteration 11 planning (focus on 3-3 splits)

### Planned
- ⏳ Remaining security prompt level studies (other models)
- ⏳ AST-based detector migration for Python and JavaScript
- ⏳ Extended language support (TypeScript, Kotlin)

## Access and Reproducibility

### Repository Structure
```
AI_Security_Benchmark/
├── prompts/                    # Prompt definitions
│   ├── prompts.yaml           # Baseline prompts (Level 0)
│   └── prompts_level[1-5]_security.yaml
├── output/                     # Generated code
│   └── <model_name>/
├── reports/                    # Analysis results
├── tests/                      # 69 detector modules
├── scripts/                    # Automation tools
├── code_generator.py          # Code generation runner
└── runner.py                  # Security analysis runner
```

### Running the Benchmark

**Generate Code**:
```bash
python3 code_generator.py \
  --model gpt-4o \
  --prompts prompts/prompts.yaml \
  --output output/gpt-4o \
  --temperature 0.2
```

**Analyze Security**:
```bash
python3 runner.py \
  --code-dir output/gpt-4o \
  --output reports/gpt-4o_analysis.json \
  --model gpt-4o
```

**Cross-Model Comparison**:
```bash
python3 scripts/cross_model_validation.py \
  reports/model1_analysis.json \
  reports/model2_analysis.json \
  reports/model3_analysis.json
```

## Citation

If you use this benchmark in your research, please cite:
```
AI Security Benchmark: Comprehensive Evaluation of Code Generation Security
26 AI Models/Applications, 100+ Configurations, 760 Prompts, 200+ Vulnerability Categories
2026. https://github.com/[your-repo]
```

## Contact and Contributions

- **Issues**: Report bugs or suggest improvements via GitHub issues
- **Detector Improvements**: Submit pull requests with new detection patterns
- **Model Additions**: Request evaluation of additional AI models
- **Research Collaboration**: Contact for academic partnerships

---

**Last Updated**: 2026-04-02
**Benchmark Version**: 3.0
**Detector Iteration**: 10
**Total Configurations**: 100+
**AI Models**: 23
**AI Applications**: 3
**Languages**: 27
