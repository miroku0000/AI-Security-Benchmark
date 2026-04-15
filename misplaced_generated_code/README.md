# Misplaced Generated Code

This directory contains AI-generated code samples that were incorrectly placed in the project root directory.

## Summary

- **Total items moved**: 287 (79 files + 207 directories + 1 directory created)
- **Date cleaned**: 2026-04-03
- **Reason**: These are AI-generated code samples from benchmark tests that should have been in model output directories

## Contents

### Files (79 total)
AI-generated code files including:
- Web APIs (Express, Flask, FastAPI, etc.)
- Cloud functions (AWS Lambda, Azure Functions, GCP Cloud Functions, Cloudflare Workers)
- Mobile apps (iOS Swift, Android Java/Kotlin)
- Microservices (various frameworks)
- Smart contracts (Solidity)
- IoT devices (ESP32, etc.)

### Directories (207 total)
Project directories for AI-generated applications including:
- Microservices and APIs
- Cloud deployments
- Mobile applications
- Web applications
- Smart contract projects
- IoT projects
- Data science projects
- DevOps automation

## Proper Location

These files should ideally be in model-specific output directories like:
- `output/claude-opus-4-6/`
- `output/gpt-4o/`
- `output/deepseek-coder/`
- etc.

## Action Required

Review these files to determine:
1. Which model generated them
2. Which prompt they correspond to
3. Whether they should be kept or deleted
4. If kept, move to appropriate model output directory

## Project Structure (After Cleanup)

The AI_Security_Benchmark root directory now contains only:
- `prompts/` - Test prompts
- `output/` - Model output directories
- `reports/` - Analysis reports
- `tests/` - Detector test suites
- `scripts/` - Analysis and utility scripts
- `logs/` - Execution logs
- `docs/` - Documentation
- `analysis/` - Analysis tools
- `bootstrap/`, `charts/`, `ci/` - Infrastructure
- Python analysis scripts (analyze_*.py, auto_benchmark.py, etc.)
