# Claude Code CLI Security Benchmark

**Status**: ✅ COMPLETE (Updated May 2026)
**Final Score**: 1025/1616 (63.4%) - Significant wrapper improvement over raw API

---

## What is Claude Code CLI?

**Claude Code** is Anthropic's official command-line interface for Claude, providing enhanced security features and improved code generation compared to raw API access.

### Key Features
- **Version**: Latest Claude Code CLI
- **Base Model**: Claude Sonnet 4.5
- **Modes**: Interactive and batch processing
- **Integration**: Deep system integration with file/directory access
- **Security**: Enhanced prompting and safety features

---

## Benchmark Results

### Performance Summary

| Configuration | Score | Percentage | Improvement vs Raw API |
|--------------|-------|------------|----------------------|
| **Claude Code CLI** | **1025/1616** | **63.4%** | **+8.2 pp** |
| Claude Sonnet 4.5 (Raw API) | 899/1628 | 55.2% | Baseline |

**Key Finding**: Claude Code CLI demonstrates **measurable security improvement** (+8.2 percentage points) over the raw Claude Sonnet 4.5 API, showing that wrapper engineering provides real security benefits.

### Ranking Context
- **Rank**: #3 overall (out of 27 configurations)
- **Category**: Top wrapper application 
- **Outperforms**: Raw flagship APIs including GPT-4o (56.4%), Claude Opus (56.4%)
- **Behind**: Codex.app configurations (83.8%, 78.7%) and StarCoder2 (62.8%)

### Security Categories Performance
Claude Code CLI shows consistent improvements across vulnerability categories compared to raw Claude Sonnet 4.5, particularly in:
- Input validation and sanitization
- Secure coding pattern adoption
- Cryptographic implementation
- Authentication and authorization

---

## Technical Analysis

### Wrapper Engineering Impact
The +8.2 percentage point improvement demonstrates that **application-level security engineering works**:
- Enhanced prompting templates
- Security-aware context injection
- Built-in safety rails and checks
- Improved code generation patterns

### Comparison with Other Wrappers
| Wrapper | Base Model | Improvement | Score |
|---------|------------|-------------|-------|
| Codex.app + Security Skill | GPT-5.4 | +24.3 pp | 83.8% |
| Codex.app (Baseline) | GPT-5.4 | +19.2 pp | 78.7% |
| **Claude Code CLI** | **Claude Sonnet 4.5** | **+8.2 pp** | **63.4%** |
| Cursor Agent | Multiple | N/A (no single baseline) | 58.9% |

---

## Methodology

**Test Scale**: 1628-point benchmark (730 prompts across 35+ languages)
**Scoring**: 0-2 points per prompt (Vulnerable=0, Partial=1, Secure=2)
**Date**: Updated May 2026 with full benchmark results
**Reproducibility**: Results represent single-run measurements due to LLM non-determinism

---

## Conclusion

Claude Code CLI provides **meaningful security improvements** over raw API access, demonstrating that wrapper applications can enhance AI code generation security through better prompting and safety features. While not achieving the dramatic improvements seen in Codex.app configurations, the +8.2 percentage point gain represents real progress in secure AI code generation.

**Recommendation**: Use Claude Code CLI for production code generation when security is a priority, as it consistently outperforms raw API access across vulnerability categories.