# AI Security Benchmark - Quick Reference Card

## 🚀 Quick Commands

```bash
# Full benchmark (all models, all phases)
python3 run_benchmark.py --all

# Test specific models only
python3 run_benchmark.py --models "starcoder2:7b,gpt-4"

# Retest using existing code
python3 run_benchmark.py --all --skip-generation

# Only generate reports (no testing)
python3 run_benchmark.py --all --phases report --skip-checks

# Generate code only (no testing)
python3 run_benchmark.py --all --phases generate

# Test only (skip code generation)
python3 run_benchmark.py --all --phases test --skip-generation
```

## 📁 Important Files

| File | Purpose |
|------|---------|
| `run_benchmark.py` | Main pipeline script |
| `benchmark_config.yaml` | Configuration (models, timeouts, etc) |
| `PIPELINE_GUIDE.md` | Complete documentation |
| `README_PIPELINE.md` | Quick start guide |
| `COMPREHENSIVE_RESULTS_PERCENTILE.md` | **Main results** (recommended) |
| `COMPREHENSIVE_RESULTS_208POINT.md` | Traditional scoring |

## ⚙️ Configuration Quick Edit

Edit `benchmark_config.yaml`:

```yaml
models:
  openai:
    - gpt-4     # Add/remove models here
  ollama:
    - starcoder2:7b

parallel_ollama: true     # Parallel execution for local models
timeout_per_model: 3600   # Max seconds per model
```

## 🔑 Environment Variables

```bash
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."
```

## 📊 Understanding Scores

### Percentile-Based (Recommended)
```
Score = (Points Earned / Max Possible) × 100
```
- **Fair**: Excludes failed generations from denominator
- **Use for**: Models with different completion rates

### Traditional 208-Point
```
Score = Points Earned / 208
```
- **Simple**: Raw points out of 208
- **Use for**: All models completed all tests

## 🎯 Typical Workflows

### 1. Initial Benchmark Run
```bash
python3 run_benchmark.py --all
```
**Result:** Complete reports with rankings

### 2. Add New Model
```bash
# Edit benchmark_config.yaml, add model
python3 run_benchmark.py --models "new-model"
```
**Result:** New model tested, reports regenerated

### 3. Retest After Code Changes
```bash
python3 run_benchmark.py --all --phases "test,report"
```
**Result:** Tests rerun, reports regenerated

### 4. Quick Report Refresh
```bash
python3 run_benchmark.py --all --phases report --skip-checks
```
**Result:** Reports regenerated from existing test results (instant)

## 🔍 Output Locations

```
reports/
├── starcoder2:7b_208point_20260208_123456.json   ← Detailed JSON
├── starcoder2:7b_208point_20260208_123456.html   ← Interactive HTML
└── ... (one per model)

COMPREHENSIVE_RESULTS_PERCENTILE.md  ← 📌 START HERE
COMPREHENSIVE_RESULTS_208POINT.md    ← Traditional scoring
BENCHMARK_SUMMARY.md                 ← Quick table
```

## 🐛 Common Issues

| Issue | Solution |
|-------|----------|
| "OPENAI_API_KEY not found" | `export OPENAI_API_KEY="sk-..."` |
| "Ollama not responding" | `ollama serve` |
| "Model not found" (Ollama) | `ollama pull model-name` |
| Timeout errors | Edit `benchmark_config.yaml`, increase `timeout_per_model` |
| Out of memory (parallel) | Set `parallel_ollama: false` in config |

## 📈 Performance Tips

- **Parallel Ollama**: Set `parallel_ollama: true` (3x faster for local models)
- **Partial runs**: Use `--models` to test subset
- **Skip generation**: Use `--skip-generation` for retests (saves hours)
- **Report only**: Use `--phases report` for instant report updates

## 🎓 Example Use Cases

### Compare two models
```bash
python3 run_benchmark.py --models "starcoder2:7b,claude-opus-4-6"
```

### Test local models only (free)
```bash
# Edit config, keep only ollama models
python3 run_benchmark.py --all
```

### Monthly automated benchmark
```bash
#!/bin/bash
# cron: 0 0 1 * *
python3 run_benchmark.py --all
DATE=$(date +%Y%m)
cp COMPREHENSIVE_RESULTS_*.md archive/$DATE/
```

## 📖 Documentation Hierarchy

1. **QUICK_REFERENCE.md** ← You are here (1-page cheat sheet)
2. **README_PIPELINE.md** ← Quick start guide (5 min read)
3. **PIPELINE_GUIDE.md** ← Complete documentation (20 min read)

## 🆘 Help

```bash
# Get command help
python3 run_benchmark.py --help

# View documentation
cat README_PIPELINE.md
cat PIPELINE_GUIDE.md
```

---

**Last Updated:** February 8, 2026
