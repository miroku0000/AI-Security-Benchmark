# Comprehensive Temperature Study - All Models

A complete temperature impact study across all 23 temperature-supporting models.

## Overview

This study tests how the temperature parameter affects security vulnerability rates in AI-generated code across:
- **23 models** from 4 providers (OpenAI, Anthropic, Google, Ollama)
- **5 temperature values** (0.0, 0.2, 0.5, 0.7, 1.0)
- **66 security prompts** across 10 vulnerability categories
- **208-point scale** (higher = more secure)

**Total test runs**: 115 (23 models × 5 temperatures)

## Models Tested

### OpenAI GPT Series (8 models)
- gpt-3.5-turbo
- gpt-4
- gpt-4o
- gpt-4o-mini
- chatgpt-4o-latest
- gpt-5.2
- gpt-5.4
- gpt-5.4-mini

### Anthropic Claude (2 models)
- claude-opus-4-6
- claude-sonnet-4-5

### Google Gemini (1 model)
- gemini-2.5-flash

### Ollama Local Models (9 models)
- codellama
- deepseek-coder
- deepseek-coder:6.7b-instruct
- starcoder2
- codegemma
- mistral
- llama3.1
- qwen2.5-coder
- qwen2.5-coder:14b

### Excluded Models (No Temperature Support)
- o1, o3, o3-mini (OpenAI o-series - fixed temperature=1.0)

## Quick Start

### Run Full Study (115 tests)

```bash
# Run all tests and generate reports
./scripts/temperature_study_all_models.sh
```

**Estimated time**:
- API models: ~2-4 hours (parallel execution)
- Ollama models: ~6-8 hours (sequential execution to avoid resource exhaustion)
- **Total**: ~8-12 hours

### Run Partial Studies

```bash
# Generate reports from existing test data (no new tests)
./scripts/temperature_study_all_models.sh --report-only

# Skip test execution, only generate reports
./scripts/temperature_study_all_models.sh --skip-generation
```

## Prerequisites

### API Keys

```bash
# OpenAI (for GPT models)
export OPENAI_API_KEY='sk-...'

# Anthropic (for Claude models) - use MYANTHROPIC_API_KEY to avoid Claude Code conflicts
export MYANTHROPIC_API_KEY='sk-ant-...'

# Google (for Gemini models)
export GEMINI_API_KEY='...'
```

### Ollama Models

```bash
# Install Ollama
brew install ollama

# Pull models you want to test
ollama pull codellama
ollama pull deepseek-coder
ollama pull starcoder2
ollama pull codegemma
ollama pull mistral
ollama pull llama3.1
ollama pull qwen2.5-coder
# ... etc
```

### Python Dependencies

```bash
pip install -r requirements.txt
```

## What the Script Does

### 1. Prerequisites Check
- Verifies API keys are set
- Checks which Ollama models are available
- Validates Python dependencies

### 2. Test Execution
For each of the 23 models:
- Runs benchmark at temperature 0.0
- Runs benchmark at temperature 0.2
- Runs benchmark at temperature 0.5
- Runs benchmark at temperature 0.7
- Runs benchmark at temperature 1.0

**Features**:
- ✅ Automatic retries (3 attempts per test)
- ✅ Resumable (uses cache - rerunning skips completed tests)
- ✅ Progress tracking
- ✅ Detailed logging
- ✅ Claude API key isolation (no conflicts with Claude Code)

### 3. Report Generation

**Individual Model Reports**:
```
reports/temperature_study_YYYYMMDD/
├── gpt-4o_temperature_analysis.txt
├── claude-opus-4-6_temperature_analysis.txt
├── gemini-2.5-flash_temperature_analysis.txt
├── codellama_temperature_analysis.txt
└── ... (one per model)
```

**Comparative Summary**:
```
reports/temperature_study_YYYYMMDD/temperature_study_summary.txt
```

Shows:
- Average security score by temperature (per provider)
- Best/worst temperature for each provider
- Temperature impact magnitude (percentage point difference)
- Key findings across all models

**HTML Reports**:
```
reports/html/index.html
```

Interactive visualizations with:
- Syntax-highlighted vulnerable code
- Side-by-side model comparisons
- Temperature impact charts
- Detailed vulnerability explanations

## Output Format

### Console Output

```
[12:34:56] Checking prerequisites...
[12:34:56] ✓ OPENAI_API_KEY found
[12:34:56] ✓ MYANTHROPIC_API_KEY found
[12:34:56] ✓ GEMINI_API_KEY found
[12:34:56] ✓ Ollama found

========================================================================
COMPREHENSIVE TEMPERATURE STUDY
========================================================================
Models: 23 (OpenAI: 8, Claude: 2, Gemini: 1, Ollama: 9)
Temperatures: 0.0 0.2 0.5 0.7 1.0
Total test runs: 115
Excluded models (no temp support): o1 o3 o3-mini
========================================================================

[12:35:00] Testing gpt-3.5-turbo at temperature 0.0
[12:36:15] ✓ Completed gpt-3.5-turbo at temp 0.0
[12:36:15] Progress: 1/115 tests completed
...
```

### Log File

```
temperature_study_20260320_123456.log
```

Complete execution log with:
- Timestamp for each test
- Success/failure status
- Error details
- API responses
- Report generation output

### Summary Report Example

```
================================================================================
TEMPERATURE IMPACT ON CODE SECURITY - COMPREHENSIVE STUDY
================================================================================

OpenAI (GPT)
================================================================================
Temperature     Avg Score       Avg %           Models Tested
--------------------------------------------------------------------------------
0.0             85.3            41.0%           8
0.2             92.1            44.3%           8
0.5             94.8            45.6%           8
0.7             98.2            47.2%           8
1.0             89.7            43.1%           8

Best temperature:  0.7 (47.2%)
Worst temperature: 0.0 (41.0%)
Temperature impact: 6.2 percentage points

Anthropic (Claude)
================================================================================
...

KEY FINDINGS
================================================================================
- Higher temperatures (0.7) generally produce MORE secure code for OpenAI models
- Claude models show different pattern: peak security at temperature 0.5
- Ollama models vary widely - some benefit from higher temp, others prefer lower
- Temperature 0.0 (deterministic) is consistently WORST for security
```

## Research Questions

This study can help answer:

1. **Does temperature affect security consistently across providers?**
   - Compare OpenAI vs Claude vs Google vs Ollama patterns

2. **What's the optimal temperature for security?**
   - Identify best temperature per model
   - Find universal optimal temperature (if exists)

3. **Do local models behave differently than API models?**
   - Compare Ollama patterns vs OpenAI/Claude/Google

4. **Is there a security-quality tradeoff?**
   - Higher temperature = more creative but less secure?
   - Or higher temperature = more defensive programming?

5. **Which models are most temperature-sensitive?**
   - Measure temperature impact magnitude per model
   - Identify stable vs volatile models

## Advanced Usage

### Test Specific Provider Only

```bash
# Modify the script to comment out unwanted provider sections
# For example, to test only OpenAI models:
# 1. Edit scripts/temperature_study_all_models.sh
# 2. Comment out Claude, Gemini, and Ollama test sections
# 3. Run: ./scripts/temperature_study_all_models.sh
```

### Custom Temperature Values

```bash
# Edit the script and modify this line:
TEMPS=(0.0 0.2 0.5 0.7 1.0)

# Example: Test extreme temperatures
TEMPS=(0.0 0.5 1.0 1.5 2.0)
```

### Resume Interrupted Study

The script is fully resumable:
```bash
# If study was interrupted, just rerun
./scripts/temperature_study_all_models.sh

# Cached results are reused, only missing tests run
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Script fails immediately | Check API keys are set: `echo $OPENAI_API_KEY` |
| Claude models fail | Verify `MYANTHROPIC_API_KEY` is set (not `ANTHROPIC_API_KEY`) |
| Ollama model not found | Run `ollama pull <model-name>` first |
| Out of memory (Ollama) | Ollama models run sequentially (not parallel) to prevent this |
| API rate limits | Script has automatic retries; wait or reduce concurrent tests |
| Report generation fails | Ensure you have test data in `reports/` directory |

## Cost Estimation

### API Costs (Approximate)

**Per model at 5 temperatures**:
- 66 prompts × 5 temperatures = 330 code generations
- Average cost per generation varies by model

**OpenAI** (8 models):
- GPT-3.5-turbo: ~$1-2 per model ($8-16 total)
- GPT-4o: ~$10-15 per model ($80-120 total)
- GPT-5 models: Higher (check current pricing)

**Anthropic** (2 models):
- Claude Opus: ~$15-25 per model ($30-50 total)
- Claude Sonnet: ~$5-10 per model ($10-20 total)

**Google** (1 model):
- Gemini Flash: ~$1-3 per model

**Ollama** (9 models):
- Free (local execution)

**Estimated total cost**: $150-300 (depending on model selection)

### Time Requirements

- **OpenAI**: 2-3 hours (parallel)
- **Claude**: 1-2 hours (parallel)
- **Gemini**: 30-60 minutes
- **Ollama**: 6-8 hours (sequential, resource-limited)

**Total**: 8-12 hours

## Files Generated

```
reports/
├── temperature_study_20260320/
│   ├── temperature_study_summary.txt          # Cross-model comparison
│   ├── gpt-4o_temperature_analysis.txt        # Individual model reports
│   ├── claude-opus-4-6_temperature_analysis.txt
│   └── ... (23 model reports)
├── html/
│   └── index.html                             # Interactive visualizations
└── *_208point_*.json                          # Raw test results (115 files)

temperature_study_20260320_123456.log          # Complete execution log
```

## Publication & Sharing

Results from this study can be:
- Published as research paper/blog post
- Shared on GitHub as benchmark results
- Used to guide model selection for security-critical code generation
- Cited in model documentation/recommendations

**Attribution**: If you publish results, please credit the AI Security Benchmark project.

## Next Steps

After running the study:

1. **Review summary report**
   ```bash
   cat reports/temperature_study_*/temperature_study_summary.txt
   ```

2. **Explore HTML visualizations**
   ```bash
   open reports/html/index.html
   ```

3. **Analyze individual models**
   ```bash
   ls reports/temperature_study_*/*.txt
   ```

4. **Share findings**
   - Create visualizations (charts, graphs)
   - Write blog post or paper
   - Update model recommendations

## See Also

- [TEMPERATURE_TESTING.md](TEMPERATURE_TESTING.md) - Single model temperature testing
- [TEMPERATURE_SUPPORT.md](TEMPERATURE_SUPPORT.md) - Which models support temperature
- [OLLAMA_TEMPERATURE_UPDATE.md](OLLAMA_TEMPERATURE_UPDATE.md) - Ollama implementation details
