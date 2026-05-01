# SAST Tool Commands - Quick Reference

## 🎯 Efficiency Improvement: SAST-First Analysis

The tool now uses a **SAST-first approach** for LLM analysis:
- **Old**: Loop through 225+ benchmark vulns → find matches in ~10 SAST findings 
- **New**: Loop through ~10 SAST findings → find matches in 225+ benchmark vulns
- **Result**: 20x+ faster analysis that answers "Are these SAST findings true/false positives?"

## 🌐 Web User Interface

**Quick Start:**
```bash
# Start web UI
python3 -m web_ui.app

# Open browser to: http://127.0.0.1:5000
```

## 🚀 One-Step Scan & Analyze Commands

### SQL Injection Analysis
```bash
# Scan with Semgrep
semgrep --config=p/sql-injection --json --output=results/semgrep_sql_results.json testsast/knownbad/sql_injection

# Basic HTML report
python3 sast_comparison.py --benchmark testsast/reports.json --sast-results results/semgrep_sql_results.json --format semgrep --category sql_injection --html results/sql_injection_report.html --scanned-dir testsast/knownbad/sql_injection

# AI-assisted analysis (auto-starts Ollama!)
python3 sast_comparison.py --benchmark testsast/reports.json --sast-results results/semgrep_sql_results.json --format semgrep --category sql_injection --llm-assist --llm-model ollama:codellama --llm-save results/sql_llm_mapping.json --scanned-dir testsast/knownbad/sql_injection
```

### XSS Analysis
```bash
semgrep --config=p/xss --json --output=results/semgrep_xss_results.json testsast/knownbad/xss
python3 sast_comparison.py --benchmark testsast/reports.json --sast-results results/semgrep_xss_results.json --format semgrep --category xss --html results/xss_report.html --scanned-dir testsast/knownbad/xss
```

### Command Injection Analysis
```bash
semgrep --config=p/command-injection --json --output=results/semgrep_cmd_results.json testsast/knownbad/command_injection
python3 sast_comparison.py --benchmark testsast/reports.json --sast-results results/semgrep_cmd_results.json --format semgrep --category command_injection --html results/cmd_injection_report.html --scanned-dir testsast/knownbad/command_injection
```

## 🎯 Key Options

| Option | Description |
|--------|-------------|
| `--llm-assist` | Enable AI-powered vulnerability matching |
| `--llm-model ollama:codellama` | Use CodeLlama model (auto-starts Ollama) |
| `--llm-review` | Interactive review of AI suggestions |
| `--interactive` | Manual vulnerability mapping mode |
| `--save-mapping FILE` | Save mappings for reuse |
| `--load-mapping FILE` | Load existing mappings |
| `--html FILE` | Generate interactive HTML report |

## 🔄 Batch Processing All Categories

```bash
#!/bin/bash
categories=(
    "sql_injection"
    "xss" 
    "command_injection"
    "path_traversal"
    "ssrf"
    "hardcoded_secrets"
)

for category in "${categories[@]}"; do
    echo "🔍 Processing $category..."
    
    # Scan with Semgrep
    semgrep --config=p/$category --json --output=results/semgrep_${category}_results.json testsast/knownbad/$category
    
    # Generate AI-assisted analysis
    python3 sast_comparison.py \
        --benchmark testsast/reports.json \
        --sast-results results/semgrep_${category}_results.json \
        --format semgrep \
        --category $category \
        --llm-assist \
        --llm-model ollama:codellama \
        --llm-save results/${category}_llm_mapping.json \
        --html results/${category}_report.html \
        --scanned-dir testsast/knownbad/$category
done
```

## 📊 Available Vulnerability Categories

- `sql_injection` (189 cases)
- `command_injection` (221 cases) 
- `path_traversal` (196 cases)
- `insecure_deserialization` (208 cases)
- `hardcoded_secrets` (172 cases)
- `ssrf` (154 cases)
- `xss` (153 cases)
- `insecure_upload` (131 cases)
- `open_redirect` (80 cases)
- `insecure_jwt` (24 cases)
- `insecure_crypto` (3 cases)

## 🛠️ Testing Auto-Start Feature

```bash
# Test Ollama auto-start
python3 test_auto_start.py

# Manual Ollama management
ollama serve          # Start manually
ollama list          # List models
ollama pull codellama # Download model
```

## 📁 Output Files

All results are organized in the `results/` directory:
- `semgrep_*_results.json` - Raw SAST scanner output
- `*_report.html` - Interactive analysis reports  
- `*_mapping.json` - Vulnerability mappings
- `*_llm_mapping.json` - AI-assisted mappings