# LLM-Assisted Vulnerability Matching

Enhance your SAST vulnerability analysis with AI-powered intelligent matching using local Large Language Models (LLMs).

## 🤖 Overview

The LLM-assisted matching feature uses local language models to intelligently match benchmark vulnerabilities with SAST tool findings. Unlike traditional rule-based matching that relies on exact file paths and line numbers, LLM matching uses semantic analysis to understand the context and meaning of vulnerabilities.

## ✨ Benefits

- **Intelligent Matching**: Understands vulnerability semantics beyond exact text matches
- **Context Aware**: Analyzes file paths, descriptions, and vulnerability types together  
- **Configurable**: Adjustable confidence thresholds and model selection
- **Privacy-First**: Uses local LLMs - no data sent to external services
- **Auditable**: Provides reasoning for each match suggestion
- **Web UI Compatible**: Generates mapping files that work with the web interface

## 🚀 Quick Start

### 1. Install Requirements

```bash
# Install Python dependencies
pip install -r requirements-llm.txt

# Install Ollama (local LLM service)
curl -fsSL https://ollama.ai/install.sh | sh

# Start Ollama service (localhost-only for security)
OLLAMA_HOST=127.0.0.1:11434 ollama serve
```

### 2. Run Setup Script

```bash
python setup_llm.py
```

This will:
- ✅ Check all dependencies
- 📦 Install a recommended model (CodeLlama)
- 🧪 Test the LLM connection
- 📚 Show usage examples

### 3. Use LLM-Assisted Matching

```bash
python sast_comparison.py \
    --benchmark testsast/reports.json \
    --sast-results semgrep_output.json \
    --format semgrep \
    --llm-assist
```

## 📋 Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--llm-assist` | Enable LLM-assisted matching | - |
| `--llm-model` | Model to use | `ollama:codellama` |
| `--llm-url` | LLM API base URL | `http://localhost:11434` |
| `--llm-confidence` | Minimum confidence (0.0-1.0) | `0.8` |
| `--llm-review` | Interactive review mode | - |
| `--llm-save` | Save matches to mapping file | - |

## 📖 Usage Examples

### Basic Auto-Matching
```bash
python sast_comparison.py \
    --benchmark reports.json \
    --sast-results scanner_output.json \
    --format semgrep \
    --llm-assist
```

### High Confidence Only
```bash
python sast_comparison.py \
    --benchmark reports.json \
    --sast-results scanner_output.json \
    --format semgrep \
    --llm-assist \
    --llm-confidence 0.9
```

### Interactive Review Mode
```bash
python sast_comparison.py \
    --benchmark reports.json \
    --sast-results scanner_output.json \
    --format semgrep \
    --llm-assist \
    --llm-review
```

### Save Mappings for Web UI
```bash
python sast_comparison.py \
    --benchmark reports.json \
    --sast-results scanner_output.json \
    --format semgrep \
    --llm-assist \
    --llm-save llm_mappings.json

# Later, load in web UI or CLI:
python sast_comparison.py \
    --benchmark reports.json \
    --sast-results scanner_output.json \
    --format semgrep \
    --load-mapping llm_mappings.json
```

### Use Different Model
```bash
python sast_comparison.py \
    --benchmark reports.json \
    --sast-results scanner_output.json \
    --format semgrep \
    --llm-assist \
    --llm-model ollama:llama2
```

## 🎯 How It Works

### 1. Candidate Selection
The system first finds potential candidates using traditional matching:
- **File similarity** (same file = highest priority)
- **Line proximity** (closer lines = higher priority)  
- **Type similarity** (similar vulnerability types)

### 2. LLM Analysis
For each benchmark vulnerability with candidates, the LLM analyzes:
- **File locations** and their relationships
- **Vulnerability types** and semantic equivalence
- **Descriptions** for context clues
- **Line proximity** and code structure

### 3. Confidence Scoring
The LLM assigns confidence scores:
- **0.95+**: Nearly identical (same file, same line, same type)
- **0.85-0.94**: Very likely match (same file, close lines, equivalent types)
- **0.70-0.84**: Probable match (related files or similar patterns)
- **0.50-0.69**: Possible match (some similarities but uncertain)

### 4. Results Processing
- Filter matches by confidence threshold
- Provide human-readable reasoning
- Optional interactive review
- Export to CLI-compatible mapping format

## 📊 Example Output

```
🤖 Starting LLM analysis with ollama:codellama
📊 Analyzing 15 benchmark vulns against 23 SAST findings

🔍 Analyzing 1/15: sql_injection in login.php
   📋 Found 3 candidates
   ✅ 1 high confidence matches found

🔍 Analyzing 2/15: xss in search.php  
   📋 Found 2 candidates
   ⚠️  1 low confidence matches

...

📈 LLM Analysis Statistics:
   Total vulnerabilities analyzed: 15
   High confidence matches found: 8
   API calls made: 15
   Match success rate: 53.3%

✅ High Confidence Matches (≥80%):
   1. 95% - Same file (login.php), adjacent lines (42 vs 43), both SQL injection vulnerabilities
   2. 88% - Same file (search.php), line proximity (18 vs 19), XSS pattern match
   3. 92% - Same file (file.php), exact line match (67), path traversal equivalent types

💾 LLM mappings saved to: llm_mappings.json
   Load with: --load-mapping llm_mappings.json
```

## 🔧 Supported Models

### Ollama (Recommended)
- **CodeLlama**: Best for code analysis (7B, 13B, 34B)
- **Llama2**: General purpose, good performance (7B, 13B, 70B)  
- **Mistral**: Fast and accurate (7B)
- **DeepSeek-Coder**: Code-specialized model

```bash
# Install models
ollama pull codellama      # 7B - good balance
ollama pull codellama:13b  # 13B - better quality
ollama pull mistral        # 7B - fastest
```

### OpenAI-Compatible APIs
You can also use OpenAI-compatible local APIs:

```bash
python sast_comparison.py \
    --llm-assist \
    --llm-model openai:gpt-3.5-turbo \
    --llm-url http://localhost:8000
```

## ⚡ Performance Tips

### Model Selection
- **CodeLlama 7B**: Good balance of speed and accuracy
- **CodeLlama 13B**: Better quality, slower inference
- **Mistral 7B**: Fastest inference, good for large datasets

### Optimization
- Use `--llm-confidence 0.8` or higher to reduce false positives
- Enable `--llm-review` for critical analysis
- Process smaller batches for memory-constrained systems

### Hardware Recommendations
- **Minimum**: 8GB RAM, 4GB VRAM (for 7B models)
- **Recommended**: 16GB RAM, 8GB VRAM (for 13B models)
- **Optimal**: 32GB RAM, 16GB VRAM (for 34B models)

## 🔒 Security & Privacy

- **Local Processing**: All analysis happens on your machine
- **No External Calls**: No data sent to cloud services
- **Localhost-Only Access**: Ollama configured for 127.0.0.1:11434 binding only
- **Audit Trail**: Full reasoning provided for each match
- **Deterministic**: Same input produces same results
- **Network Isolation**: No external network access required during operation

### Security Configuration

**⚠️ CRITICAL: Configure Ollama for localhost-only access**

```bash
# Run security audit and configuration
python secure_ollama_config.py

# Manual configuration
export OLLAMA_HOST=127.0.0.1:11434
ollama serve

# Verify security
netstat -tlnp | grep 11434  # Should show 127.0.0.1:11434, NOT 0.0.0.0:11434
```

**Security Best Practices:**
- Always run `python secure_ollama_config.py` after installation
- Verify Ollama binds to localhost only: `127.0.0.1:11434`
- Use firewall rules to block external access to port 11434
- Regularly audit configuration with security script
- Keep Ollama updated: `ollama update`

## 🐛 Troubleshooting

### Common Issues

**"Cannot connect to LLM service"**
```bash
# Check if Ollama is running
ollama list

# Start Ollama service
ollama serve

# Test connection
curl http://localhost:11434/api/tags
```

**"Model not found"**
```bash
# List available models
ollama list

# Pull required model
ollama pull codellama
```

**"Out of memory"**
- Use smaller model (7B instead of 13B)
- Reduce batch size with confidence threshold
- Close other applications

### Getting Help

1. **Check setup**: Run `python setup_llm.py`
2. **Test connection**: Use `--llm-assist` with simple dataset
3. **Review logs**: LLM errors are printed to console
4. **Model issues**: Try different model with `--llm-model`

## 🎛️ Advanced Configuration

### Custom Prompts
The LLM prompt can be customized by modifying the `_build_analysis_prompt()` method in `llm_matcher.py`.

### New Model Support
Add support for new LLM services by extending the `LLMAssistedMatcher` class.

### Integration with CI/CD
```bash
#!/bin/bash
# CI/CD integration example

# Ensure Ollama is running
ollama serve &
sleep 5

# Run LLM-assisted analysis
python sast_comparison.py \
    --benchmark baseline.json \
    --sast-results "$SAST_OUTPUT" \
    --format semgrep \
    --llm-assist \
    --llm-confidence 0.85 \
    --llm-save results/llm_mappings.json \
    --output results/analysis.json
```

## 📈 Roadmap

- **Multi-model ensemble**: Combine multiple models for better accuracy
- **Fine-tuning**: Train models on domain-specific vulnerability data
- **Batch processing**: Optimize for large-scale analysis
- **Real-time learning**: Learn from user feedback to improve suggestions
- **Advanced reasoning**: Include code context and dataflow analysis

---

For more information, see the [main documentation](README.md) or run `python setup_llm.py` to get started.