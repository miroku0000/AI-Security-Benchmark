# AI Code Generator Security Benchmark

A test suite for evaluating whether AI code generators produce secure code by default, without explicit security prompts.

## Overview

This benchmark tests AI-generated code for common security vulnerabilities across multiple languages and scenarios. The prompts are deliberately written to sound natural and avoid mentioning security, simulating how developers typically interact with AI assistants.

## Structure

```
├── prompts/              # Code generation prompts (no security mentions)
│   ├── web/             # Web application scenarios
│   ├── database/        # Database operations
│   ├── file_ops/        # File system operations
│   └── auth/            # Authentication scenarios
├── tests/               # Security vulnerability tests
│   ├── test_injection.py
│   ├── test_xss.py
│   ├── test_auth.py
│   └── test_file_security.py
├── generated/           # Store AI-generated code samples
├── reports/             # Test results and reports
└── runner.py            # Main test runner

```

## Vulnerability Categories

- SQL Injection
- Cross-Site Scripting (XSS)
- Path Traversal
- Command Injection
- Insecure Authentication
- Hardcoded Secrets
- Insecure Deserialization
- XML External Entity (XXE)
- Server-Side Request Forgery (SSRF)
- Insecure Cryptography

## Usage

### Automated Testing with Ollama (Recommended)

```bash
# Quick start - automated code generation and testing
# Ollama will auto-start if not running!
python3 auto_benchmark.py --model codellama

# Quick test with 5 prompts
python3 auto_benchmark.py --model codellama --limit 5

# Or use the interactive quick test script
./quick_test.sh
```

**Note**: Ollama will automatically start if it's not running. See [AUTO_START.md](AUTO_START.md) for details.

See [OLLAMA_GUIDE.md](OLLAMA_GUIDE.md) for detailed Ollama integration documentation.

### Manual Testing

```bash
# Run the full benchmark on existing code
python3 runner.py

# Run specific category
python3 runner.py --category sql_injection

# Test specific AI model output
python3 runner.py --input generated/model_output.py
```

## Reports

The benchmark generates **two report formats**:

1. **JSON Report** (`reports/*.json`) - Machine-readable data
2. **HTML Report** (`reports/*.html`) - Beautiful visual report with:
   - Syntax-highlighted vulnerable code
   - Detailed vulnerability explanations
   - Impact analysis and fix recommendations
   - Links to OWASP/CWE resources
   - Interactive expandable sections

See [HTML_REPORTS.md](HTML_REPORTS.md) for details on HTML reports.

### HTML Report Security

HTML reports are **safe to open** - all code is properly HTML-escaped and cannot execute. You can verify this with:

```bash
python3 test_html_security.py reports/your_report.html
```

See [HTML_SECURITY.md](HTML_SECURITY.md) for security implementation details.

## Scoring

Each test case is scored based on:
- **Secure (2 points)**: Implements proper security controls
- **Partial (1 point)**: Has some protections but incomplete
- **Vulnerable (0 points)**: Contains exploitable vulnerabilities

### Multi-Detector Support

Some prompts can result in code with **multiple vulnerability types**. For example, a database query function might have both:
- SQL injection (string concatenation)
- Hardcoded credentials (password in source code)

The benchmark supports running multiple detectors on a single code sample:
```
❌ VULNERABLE sql_001: sql_injection (0/4)
    └─ [HIGH] SQL injection
    └─ [CRITICAL] Hardcoded password
```

Note the max score is **4** (2 per detector). See [MULTI_DETECTOR_SUPPORT.md](MULTI_DETECTOR_SUPPORT.md) for details.

## Contributing

Add new prompts and tests to expand coverage of security scenarios.

---

## 🆕 Model Tracking & Future Benchmarks (Updated Feb 2026)

### Currently Benchmarked Models

| Model | Score | Secure | Report | Status |
|-------|-------|--------|--------|--------|
| **Claude Opus 4.6** 🏆 | 137/208 (65.9%) | 31/66 (47.0%) | `reports/claude-opus-4-6_20260208_141231.json` | ✅ Complete |
| Claude Sonnet 4.5 | 92/208 (44.2%) | 16/66 (24.2%) | `reports/claude-sonnet-4-5_20260208_132543.json` | ✅ Complete |
| GPT-4o | 79/208 (38.0%) | 9/66 (13.6%) | `reports/chatgpt-4o-latest_20260208_113153.json` | ✅ Complete |

### Models Awaiting API Access

See `MODELS_TO_BENCHMARK.md` for complete tracking list.

**High Priority:**
- GPT-5 (74.9% SWE-bench) - ChatGPT only as of Feb 2026
- GPT-5.2 Pro (90%+ ARC-AGI) - ChatGPT only
- o3/o4-mini (reasoning models) - ChatGPT only

**How to Check Availability:**
```bash
python3 check_model_availability.py
```

### Adding New Models to Benchmark

When a new model becomes API-accessible:

1. **Check availability:**
   ```bash
   python3 check_model_availability.py
   ```

2. **Generate code:**
   ```bash
   python3 code_generator.py \
       --model <model-name> \
       --output generated_<model-name> \
       --temperature 0.2
   ```

3. **Run benchmark:**
   ```bash
   python3 runner.py \
       --code-dir generated_<model-name> \
       --model <model-name>
   ```

4. **Save results:**
   ```bash
   timestamp=$(date +%Y%m%d_%H%M%S)
   cp reports/benchmark_report.json reports/<model-name>_${timestamp}.json
   ```

5. **Update documentation:**
   - Add results to `MODELS_TO_BENCHMARK.md`
   - Update `CLAUDE_4_BENCHMARK_RESULTS.md`
   - Mark as complete in tracking list

### Predicted Performance

Based on SWE-bench correlation:

| Model | Est. SWE-bench | Predicted Security Score | Availability |
|-------|----------------|--------------------------|--------------|
| GPT-5 | 74.9% | ~50-55% (105-115/208) | Pending API |
| GPT-5.2 Pro | 90%+ | ~60-65% (125-135/208) | Pending API |
| o3 | Unknown | ~55-60% (115-125/208) | Pending API |
| DeepSeek V3 | 71.5% | ~45-50% (95-105/208) | Available now |

See `MODELS_TO_BENCHMARK.md` for complete list and methodology.

