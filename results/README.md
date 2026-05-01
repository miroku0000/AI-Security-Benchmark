# SAST Comparison Tool Usage Guide

This directory contains results from SAST tool comparisons against the AI Security Benchmark.

## ✨ New Features

- **🌐 Web User Interface**: Interactive web-based analysis and mapping tool
- **🚀 Auto-Start Ollama**: The tool now automatically starts Ollama if it's not running
- **🔒 Security Checks**: Automatic verification that Ollama is configured securely (localhost-only)
- **🤖 AI-Assisted Matching**: Use local LLM models to intelligently match vulnerabilities
- **⚡ SAST-First Analysis**: Efficient analysis starting with SAST findings (much faster!)
- **🎯 True/False Positive Classification**: LLM determines if SAST findings are accurate
- **🔍 Enhanced Review Interface**: Detailed side-by-side comparison during interactive review
- **💾 Persistent Mappings**: Save and reuse vulnerability mappings across runs
- **📊 Rich HTML Reports**: Interactive web-based analysis reports

## 🌐 Web User Interface

Access the interactive web UI:

```bash
# Start the web interface
python3 -m web_ui.app

# Open in browser: http://127.0.0.1:5000
```

The web UI provides:
- **Drag & Drop File Upload**: Easy upload of benchmark and SAST result files
- **Interactive Mapping**: Visual vulnerability matching interface with detailed side-by-side comparisons
- **Resizable Layout**: Drag to resize panels, expand button for detailed analysis
- **Rich Vulnerability Display**: Full file paths, severity badges, complete descriptions
- **Confidence Adjustment**: Real-time filtering based on confidence scores
- **LLM Reasoning Display**: See why matches were suggested with detailed explanations
- **Export Capabilities**: Download mappings and analysis results

### 🎨 Enhanced Interface Features:
- **📁 Detailed vulnerability cards** with file paths, line numbers, and descriptions
- **🔄 Resizable suggestions panel** - drag the handle (⋮⋮⋮) or click expand
- **🎯 Visual match indicators** - confidence badges and quality icons
- **📊 Side-by-side comparison** showing benchmark vs SAST findings
- **🧠 LLM reasoning display** explaining match logic

## 🎯 Why SAST-First Analysis?

**Traditional approach**: Loop through 225 benchmark vulnerabilities → find matches in 10 SAST findings
**New approach**: Loop through 10 SAST findings → find matches in 225 benchmark vulnerabilities

This is **22.5x more efficient** and answers the right question: "Are these SAST findings true or false positives?"

## 🔍 Enhanced Review Interface

When using `--llm-review`, you now see detailed comparisons:

```
📋 MATCH 1/10
==================================================
🎯 CONFIDENCE: 95.0%
🧠 REASONING: Same file, adjacent lines, same vuln type

🔍 SAST TOOL FINDING:
   📁 File: sql_injection/ruby/o3-mini_ruby_001_score00.rb
   📍 Line: 24
   🚨 Type: ruby.rails.security.injection.tainted-sql-string
   ⚡ Severity: WARNING
   📝 Description: User input flows into SQL query

✅ BENCHMARK VULNERABILITY (Ground Truth):
   📁 File: sql_injection/ruby/o3-mini_ruby_001_score00.rb
   📍 Line: 24
   🚨 Type: SQL_INJECTION
   ⚡ Severity: HIGH
   📝 Description: Direct string interpolation in SQL query

📊 COMPARISON:
   ✅ Same file
   📍 Line difference: 0
   ✅ Same type

Accept this match? (y/n/s=skip/q=quit):
```

## Quick Start

### 1. Setup Ollama (Optional - for AI-assisted analysis)

**Note: The SAST comparison tool now automatically starts Ollama if needed!**

Check if Ollama is installed:
```bash
which ollama
```

If not installed, get it from: https://ollama.ai

Pull a model for code analysis (if you don't have one):
```bash
# CodeLlama (recommended for code analysis)
ollama pull codellama

# Or smaller model:
ollama pull llama3.2
```

Check available models:
```bash
ollama list
```

**Manual start (if auto-start fails):**
```bash
# In a separate terminal:
ollama serve

# Or run in background:
ollama serve &
```

### 2. Scan with Semgrep

Scan specific vulnerability categories:

```bash
# SQL Injection
semgrep --config=p/sql-injection --json --output=results/semgrep_sql_results.json testsast/knownbad/sql_injection

# Cross-Site Scripting (XSS)
semgrep --config=p/xss --json --output=results/semgrep_xss_results.json testsast/knownbad/xss

# Command Injection  
semgrep --config=p/command-injection --json --output=results/semgrep_cmd_results.json testsast/knownbad/command_injection

# Path Traversal
semgrep --config=p/path-traversal --json --output=results/semgrep_path_results.json testsast/knownbad/path_traversal

# Server-Side Request Forgery (SSRF)
semgrep --config=p/ssrf --json --output=results/semgrep_ssrf_results.json testsast/knownbad/ssrf

# Hardcoded Secrets
semgrep --config=p/secrets --json --output=results/semgrep_secrets_results.json testsast/knownbad/hardcoded_secrets

# Insecure Deserialization
semgrep --config=p/deserialization --json --output=results/semgrep_deserial_results.json testsast/knownbad/insecure_deserialization

# Open Redirect
semgrep --config=p/redirect --json --output=results/semgrep_redirect_results.json testsast/knownbad/open_redirect
```

### 3. Compare Results

Choose one of the following approaches:

#### Option A: Basic HTML Report
```bash
python3 sast_comparison.py --benchmark testsast/reports.json --sast-results results/semgrep_sql_results.json --format semgrep --category sql_injection --html results/sql_injection_report.html --scanned-dir testsast/knownbad/sql_injection
```

#### Option B: Interactive Manual Mapping
```bash
python3 sast_comparison.py --benchmark testsast/reports.json --sast-results results/semgrep_sql_results.json --format semgrep --category sql_injection --interactive --save-mapping results/sql_mapping.json --scanned-dir testsast/knownbad/sql_injection
```

#### Option C: AI-Assisted Analysis (Requires Ollama)
```bash
python3 sast_comparison.py --benchmark testsast/reports.json --sast-results results/semgrep_sql_results.json --format semgrep --category sql_injection --llm-assist --llm-model ollama:codellama --llm-review --llm-save results/sql_llm_mapping.json --scanned-dir testsast/knownbad/sql_injection
```

#### Option D: Load Previously Saved Mappings
```bash
python3 sast_comparison.py --benchmark testsast/reports.json --sast-results results/semgrep_sql_results.json --format semgrep --load-mapping results/sql_mapping.json --scanned-dir testsast/knownbad/sql_injection
```

## Available Vulnerability Categories

Based on the AI Security Benchmark, these categories are available:

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

## Batch Processing Example

Process multiple categories:

```bash
#!/bin/bash
# Scan multiple categories
semgrep --config=p/sql-injection --json --output=results/semgrep_sql_results.json testsast/knownbad/sql_injection
semgrep --config=p/xss --json --output=results/semgrep_xss_results.json testsast/knownbad/xss
semgrep --config=p/command-injection --json --output=results/semgrep_cmd_results.json testsast/knownbad/command_injection

# Generate comparison reports
python3 sast_comparison.py --benchmark testsast/reports.json --sast-results results/semgrep_sql_results.json --format semgrep --category sql_injection --html results/sql_injection_report.html --scanned-dir testsast/knownbad/sql_injection

python3 sast_comparison.py --benchmark testsast/reports.json --sast-results results/semgrep_xss_results.json --format semgrep --category xss --html results/xss_report.html --scanned-dir testsast/knownbad/xss

python3 sast_comparison.py --benchmark testsast/reports.json --sast-results results/semgrep_cmd_results.json --format semgrep --category command_injection --html results/command_injection_report.html --scanned-dir testsast/knownbad/command_injection
```

## Command Line Options

Run `python3 sast_comparison.py --help` for full option details:

- `--interactive`: Enable manual vulnerability mapping
- `--llm-assist`: Use AI to suggest vulnerability matches
- `--llm-review`: Interactively review AI suggestions
- `--save-mapping FILE`: Save mappings for future use
- `--load-mapping FILE`: Load previously saved mappings
- `--html FILE`: Generate interactive HTML report
- `--limit-per-type N`: Limit displayed vulnerabilities per type
- `--llm-confidence 0.8`: Set minimum confidence for AI matches

## File Outputs

- `semgrep_*_results.json`: Raw Semgrep scan results
- `*_mapping.json`: Vulnerability mapping files (for reuse)
- `*_report.html`: Interactive HTML analysis reports
- `*_llm_mapping.json`: AI-assisted mapping results

## Troubleshooting

### Ollama Connection Issues
The tool now auto-starts Ollama, but if you encounter issues:

```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Manually start Ollama if auto-start fails
ollama serve

# Check system processes
ps aux | grep ollama

# Kill existing Ollama processes if needed
pkill -f ollama
```

### Missing Models
```bash
# List available models
ollama list

# Pull required model
ollama pull codellama
```

### Scan Directory Issues
Make sure the `--scanned-dir` parameter matches exactly what you scanned with Semgrep. This is crucial for proper vulnerability matching.