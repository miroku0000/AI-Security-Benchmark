# AI Security Benchmark - Complete Pipeline Guide

This guide explains how to reproduce the entire benchmark from start to finish.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Prerequisites](#prerequisites)
3. [Configuration](#configuration)
4. [Running the Pipeline](#running-the-pipeline)
5. [Understanding Results](#understanding-results)
6. [Advanced Usage](#advanced-usage)
7. [Troubleshooting](#troubleshooting)

---

## Quick Start

Run the complete benchmark on all configured models:

```bash
# Set up API keys
export OPENAI_API_KEY="your-key-here"
export ANTHROPIC_API_KEY="your-key-here"

# Ensure Ollama is running
ollama list

# Run the complete pipeline
python3 auto_benchmark.py --all
```

This will:
1. Generate code for all models (Phase 1)
2. Test all generated code (Phase 2)
3. Generate comprehensive reports (Phase 3)

---

## Prerequisites

### Required Software

- **Python 3.8+**
- **pip** packages: `pyyaml`, `requests`, `anthropic`, `openai`
- **Ollama** (for local models): [Download](https://ollama.ai)

### Required API Keys

Set these as environment variables:

```bash
# OpenAI (for GPT models)
export OPENAI_API_KEY="sk-..."

# Anthropic (for Claude models)
export ANTHROPIC_API_KEY="sk-ant-..."
```

### Required Files

Your project should have:
- `prompts/prompts.yaml` - Test case definitions
- `code_generator.py` - Code generation script
- `runner.py` - Security testing script
- `benchmark_config.yaml` - Pipeline configuration

---

## Configuration

Edit `benchmark_config.yaml` to customize your benchmark:

### Selecting Models

```yaml
models:
  openai:
    - gpt-4
    - gpt-4o
    # Add or remove OpenAI models

  anthropic:
    - claude-opus-4-6
    # Add or remove Anthropic models

  ollama:
    - starcoder2:7b
    - deepseek-coder
    # Add or remove Ollama models
```

### Execution Settings

```yaml
parallel_ollama: true  # Run local models in parallel (faster)
timeout_per_model: 3600  # Max seconds per model (1 hour)
```

---

## Running the Pipeline

### Full Pipeline (All Steps)

Run everything from scratch:

```bash
python3 auto_benchmark.py --all
```

### Retest Existing Code

Skip code generation, only run tests on existing code:

```bash
python3 auto_benchmark.py --all --skip-generation
```

### Test Specific Models

Test only certain models:

```bash
python3 auto_benchmark.py --models "starcoder2:7b,gpt-4,claude-opus-4-6"
```

### Run Specific Phases

Run only certain phases:

```bash
# Only generate code
python3 auto_benchmark.py --all --phases generate

# Only run tests
python3 auto_benchmark.py --all --phases test

# Only generate reports
python3 auto_benchmark.py --all --phases report

# Multiple phases
python3 auto_benchmark.py --all --phases "test,report"
```

---

## Understanding Results

### Output Files

After running, you'll have:

```
reports/
├── starcoder2:7b_208point_20260208_123456.json
├── gpt-4_208point_20260208_123456.json
├── ...
└── (one JSON + HTML report per model)

COMPREHENSIVE_RESULTS_PERCENTILE.md  # Main results (recommended)
COMPREHENSIVE_RESULTS_208POINT.md    # Traditional scoring
BENCHMARK_SUMMARY.md                 # Quick summary table
```

### Scoring Methods

#### Percentile-Based (Recommended)

```
Score = (Points Earned / Max Possible) × 100
```

- **Fair**: Excludes failed code generations from both numerator and denominator
- **Focus**: Measures security of code that was actually generated
- **Use when**: Comparing models with different completion rates

**Example:**
- Model generates 65/66 tests (1 failed)
- Earns 181 points out of 206 possible
- Percentile: 181/206 = 87.86%

#### Traditional (208-Point)

```
Score = Points Earned / 208
```

- **Simple**: Raw points out of 208 maximum
- **Penalty**: Failed generations count as -1 point
- **Use when**: All models complete all tests

---

## Advanced Usage

### Adding New Models

1. Edit `benchmark_config.yaml`:

```yaml
models:
  ollama:
    - my-new-model:latest
```

2. For Ollama models, pull first:

```bash
ollama pull my-new-model:latest
```

3. Run benchmark:

```bash
python3 auto_benchmark.py --models "my-new-model:latest"
```

### Custom Test Cases

Edit `prompts/prompts.yaml` to add new test cases:

```yaml
test_cases:
  - id: custom_001
    category: custom_vuln
    language: python
    prompt: "Your test prompt here..."
    expected_vulnerabilities:
      - custom_vuln
```

### Parallel Execution

For faster testing, enable parallel Ollama execution in `benchmark_config.yaml`:

```yaml
parallel_ollama: true
```

This runs all Ollama models simultaneously (only works for local models, not APIs).

### Using Custom Config

Use a different configuration file:

```bash
python3 auto_benchmark.py --all --config my_config.yaml
```

---

## Pipeline Architecture

### Phase 1: Code Generation

```
For each model:
  1. Read prompts from prompts.yaml
  2. Call model API/Ollama to generate code
  3. Save to output/<model>/ directory
  4. Store 66 files (one per test case)
```

**Output:** `output/<model>/*.{py,js,java}`

### Phase 2: Security Testing

```
For each model:
  1. Load generated code from output/<model>/
  2. Run 27 security detectors on each file
  3. Calculate weighted scores
  4. Generate JSON + HTML reports
```

**Output:** `reports/<model>_208point_<timestamp>.{json,html}`

### Phase 3: Report Generation

```
1. Collect all test results
2. Calculate percentile scores (exclude failed generations)
3. Calculate traditional scores (include all)
4. Generate rankings
5. Create markdown reports
```

**Output:**
- `COMPREHENSIVE_RESULTS_PERCENTILE.md`
- `COMPREHENSIVE_RESULTS_208POINT.md`
- `BENCHMARK_SUMMARY.md`

---

## Troubleshooting

### "OPENAI_API_KEY not found"

```bash
export OPENAI_API_KEY="sk-..."
```

Or add to `~/.bashrc` / `~/.zshrc` for persistence.

### "Ollama not responding"

Start Ollama:

```bash
ollama serve
```

Or ensure it's running as a background service.

### "Model not found" (Ollama)

Pull the model first:

```bash
ollama pull starcoder2:7b
```

### Code generation timeout

Increase timeout in `benchmark_config.yaml`:

```yaml
timeout_per_model: 7200  # 2 hours
```

### Memory issues with parallel execution

Disable parallel Ollama:

```yaml
parallel_ollama: false
```

### Missing dependencies

Install required packages:

```bash
pip3 install pyyaml requests anthropic openai
```

---

## Example Workflows

### Research Use Case: Compare Two Specific Models

```bash
# Generate and test only these models
python3 auto_benchmark.py --models "starcoder2:7b,claude-opus-4-6"

# View results
cat COMPREHENSIVE_RESULTS_PERCENTILE.md
```

### Development Use Case: Test New Prompts

```bash
# 1. Edit prompts/prompts.yaml to add new test cases

# 2. Regenerate code for one model
python3 auto_benchmark.py --models "starcoder2:7b" --phases generate

# 3. Test the new code
python3 auto_benchmark.py --models "starcoder2:7b" --phases test

# 4. View individual report
open reports/starcoder2:7b_208point_*.html
```

### Production Use Case: Monthly Benchmark

```bash
#!/bin/bash
# monthly_benchmark.sh

# Set API keys
source ~/.api_keys

# Run full benchmark
python3 auto_benchmark.py --all

# Archive results
DATE=$(date +%Y%m)
mkdir -p archive/$DATE
cp COMPREHENSIVE_RESULTS_*.md archive/$DATE/
cp reports/*_208point_*.json archive/$DATE/

# Email results
mail -s "Benchmark Results $DATE" team@company.com < COMPREHENSIVE_RESULTS_PERCENTILE.md
```

---

## Extending the Pipeline

### Adding New Phases

Edit `auto_benchmark.py`:

```python
def custom_phase(self):
    print("Running custom analysis...")
    # Your code here

# In run() method:
if 'custom' in phases:
    self.custom_phase()
```

### Custom Report Formats

Add report generation in `auto_benchmark.py`:

```python
def _generate_custom_report(self):
    # Generate your custom report
    pass
```

### Integration with CI/CD

Example GitHub Actions workflow:

```yaml
name: Security Benchmark
on: [push]
jobs:
  benchmark:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run Benchmark
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: |
          python3 auto_benchmark.py --models "gpt-4,gpt-4o"
      - name: Upload Results
        uses: actions/upload-artifact@v2
        with:
          name: benchmark-results
          path: COMPREHENSIVE_RESULTS_*.md
```

---

## Best Practices

### 1. Version Control

Commit your config and results:

```bash
git add benchmark_config.yaml
git add COMPREHENSIVE_RESULTS_*.md
git commit -m "Benchmark results $(date +%Y-%m-%d)"
```

### 2. Cost Management

Estimate costs before running:
- OpenAI: ~$0.02 per test case × 66 tests = ~$1.32 per model
- Anthropic: Similar pricing
- Ollama: Free (local)

### 3. Reproducibility

Always include:
- Date and time of benchmark
- Model versions (e.g., "gpt-4-0125" not just "gpt-4")
- Configuration file
- Prompts file version

### 4. Comparison

When comparing results:
- Use percentile scoring for models with different completion rates
- Compare only models tested on the same prompt set
- Note any changes to detectors or scoring weights

---

## FAQ

**Q: How long does a full benchmark take?**
A: ~8-12 hours for 20 models (2-3 hours with parallel Ollama)

**Q: Can I run this on a cloud VM?**
A: Yes, install Ollama and set API keys. 8GB RAM recommended.

**Q: What if a model is down?**
A: Pipeline continues with other models. Failed models get empty reports.

**Q: Can I compare old and new results?**
A: Yes! Keep both markdown reports and diff them:
```bash
diff COMPREHENSIVE_RESULTS_PERCENTILE_old.md COMPREHENSIVE_RESULTS_PERCENTILE.md
```

**Q: How do I add my own proprietary model?**
A: Modify `code_generator.py` to support your API, then add to config.

---

## Support

For issues or questions:
1. Check this guide
2. Review error messages carefully
3. Check individual model reports in `reports/`
4. Verify API keys and Ollama status

---

**Last Updated:** 2026-02-08
**Version:** 2.0
