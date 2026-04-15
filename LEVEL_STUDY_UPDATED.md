# Multi-Level Security Prompting Study (Updated)

**Generated:** 2026-04-14
**Detectors Applied:** DNS rebinding detection (SSRF), HTTP Header Injection detector

## Executive Summary

Security prompting effectiveness was tested across **9 models** with **5 progressive prompting levels** (Level 1-5):

- **Anthropic Models:** Mixed results (1 improves +2.70pp, 1 regresses -0.32pp)
- **OpenAI Models:** Both improve significantly (+3.09pp to +3.35pp)
- **Ollama/Open Source:** Mostly improve (4 of 5 models improve +1.71pp to +2.44pp)

## Key Finding: Previous Claim Was BACKWARDS

**❌ OLD CLAIM (INCORRECT):**
> "Anthropic models improve +5.4pp to +6.8pp, OpenAI models improve marginally +0.2pp to +1.2pp, while most Ollama models (4 of 5) regress -1.0pp to -6.7pp"

**✅ ACTUAL RESULTS:**
- **Anthropic:** -0.32pp to +2.70pp (NOT +5.4 to +6.8pp)
- **OpenAI:** +3.09pp to +3.35pp (NOT marginal +0.2 to +1.2pp) ← **Best performers!**
- **Ollama:** Only 1 of 5 regresses (NOT 4 of 5) ← **Opposite of claim!**

---

## Detailed Results by Provider

### ANTHROPIC MODELS

#### Claude Opus 4.6
| Level | Security % | Change from L1 | Status |
|-------|-----------|----------------|---------|
| L1 (baseline) | 61.64% | — | Baseline |
| L2 | 59.87% | -1.77 pp | Worse |
| L3 | 60.46% | -1.18 pp | Worse |
| L4 | 61.84% | **+0.20 pp** | ⭐ Best |
| L5 | 61.32% | -0.32 pp | Slightly worse |

**Summary:** Minimal change (-0.32pp L1→L5). Peak at Level 4.

#### Claude Sonnet 4.5
| Level | Security % | Change from L1 | Status |
|-------|-----------|----------------|---------|
| L1 (baseline) | 59.21% | — | Baseline |
| L2 | 58.03% | -1.18 pp | Worse |
| L3 | 60.79% | +1.58 pp | Better |
| L4 | 59.80% | +0.59 pp | Better |
| L5 | 61.91% | **+2.70 pp** | ⭐ Best |

**Summary:** Improves +2.70pp (L1→L5). Best Anthropic model for security prompting.

---

### OPENAI MODELS ⭐ BEST PERFORMERS

#### GPT-4o
| Level | Security % | Change from L1 | Status |
|-------|-----------|----------------|---------|
| L1 (baseline) | 54.67% | — | Baseline |
| L2 | 55.59% | +0.92 pp | Better |
| L3 | 56.18% | +1.51 pp | Better |
| L4 | 58.75% | **+4.08 pp** | ⭐ Best |
| L5 | 57.76% | +3.09 pp | Better |

**Summary:** Improves +3.09pp (L1→L5). Peak at Level 4 (+4.08pp).

#### GPT-4o-mini
| Level | Security % | Change from L1 | Status |
|-------|-----------|----------------|---------|
| L1 (baseline) | 50.86% | — | Baseline |
| L2 | 54.08% | +3.22 pp | Better |
| L3 | 54.41% | +3.55 pp | Better |
| L4 | 59.01% | **+8.15 pp** | ⭐ Best |
| L5 | 54.21% | +3.35 pp | Better |

**Summary:** Improves +3.35pp (L1→L5). **Largest peak improvement: +8.15pp at Level 4!**

---

### OLLAMA/OPEN SOURCE MODELS

#### DeepSeek Coder
| Level | Security % | Change from L1 | Status |
|-------|-----------|----------------|---------|
| L1 (baseline) | 58.55% | — | Baseline |
| L2 | 58.49% | -0.06 pp | Stable |
| L3 | 58.16% | -0.39 pp | Slightly worse |
| L4 | 59.67% | +1.12 pp | Better |
| L5 | 60.72% | **+2.17 pp** | ⭐ Best |

**Summary:** Improves +2.17pp (L1→L5).

#### Llama 3.1
| Level | Security % | Change from L1 | Status |
|-------|-----------|----------------|---------|
| L1 (baseline) | 51.18% | — | Baseline |
| L2 | 53.36% | +2.18 pp | Better |
| L3 | 53.88% | +2.70 pp | Better |
| L4 | 56.91% | **+5.73 pp** | ⭐ Best |
| L5 | 53.62% | +2.44 pp | Better |

**Summary:** Improves +2.44pp (L1→L5). Large peak at Level 4.

#### Qwen 2.5 Coder
| Level | Security % | Change from L1 | Status |
|-------|-----------|----------------|---------|
| L1 (baseline) | 51.84% | — | Baseline |
| L2 | 54.21% | +2.37 pp | Better |
| L3 | 55.20% | +3.36 pp | Better |
| L4 | 56.38% | **+4.54 pp** | ⭐ Best |
| L5 | 53.88% | +2.04 pp | Better |

**Summary:** Improves +2.04pp (L1→L5).

#### Qwen 3 Coder 30B
| Level | Security % | Change from L1 | Status |
|-------|-----------|----------------|---------|
| L1 (baseline) | 54.80% | — | Baseline |
| L2 | 55.66% | +0.86 pp | Better |
| L3 | 56.71% | +1.91 pp | Better |
| L4 | 58.62% | **+3.82 pp** | ⭐ Best |
| L5 | 56.51% | +1.71 pp | Better |

**Summary:** Improves +1.71pp (L1→L5).

#### CodeLlama (Only Regression)
| Level | Security % | Change from L1 | Status |
|-------|-----------|----------------|---------|
| L1 (baseline) | 54.08% | — | Baseline |
| L2 | 54.61% | +0.53 pp | Better |
| L3 | 55.39% | +1.31 pp | Better |
| L4 | 56.25% | **+2.17 pp** | ⭐ Best |
| L5 | 53.68% | -0.40 pp | Worse |

**Summary:** Regresses -0.40pp (L1→L5). Only Ollama model that worsens.

---

## Provider Comparison Summary

| Provider | Models Improve | Models Regress | Avg Improvement | Avg Regression |
|----------|---------------|----------------|-----------------|----------------|
| **Anthropic** | 1 of 2 (50%) | 1 of 2 (50%) | +2.70 pp | -0.32 pp |
| **OpenAI** | 2 of 2 (100%) | 0 of 2 (0%) | **+3.22 pp** ⭐ | — |
| **Ollama** | 4 of 5 (80%) | 1 of 5 (20%) | +2.09 pp | -0.40 pp |

**Key Insight:** OpenAI models respond best to security prompting, with 100% improvement rate and highest average gain (+3.22pp).

---

## Level 4 Pattern: "The Prescriptive Peak"

**7 out of 9 models peak at Level 4:**
- GPT-4o: +4.08 pp
- GPT-4o-mini: +8.15 pp (largest)
- Llama 3.1: +5.73 pp
- Qwen 2.5 Coder: +4.54 pp
- Qwen 3 Coder 30B: +3.82 pp
- CodeLlama: +2.17 pp
- Claude Opus 4.6: +0.20 pp

**Only 2 models peak at Level 5:**
- Claude Sonnet 4.5: +2.70 pp
- DeepSeek Coder: +2.17 pp

**Conclusion:** Level 4 (prescriptive security guidance) is the sweet spot for most models. Level 5 (self-review) often causes regression.

---

## Prompting Level Definitions

1. **Level 1 (Baseline):** Standard prompts with no security guidance
2. **Level 2 (Minimal):** Brief mention of security importance
3. **Level 3 (Principles):** Security principles and best practices
4. **Level 4 (Prescriptive):** Specific security requirements and controls
5. **Level 5 (Self-Review):** Request for security review and iteration

---

## Recommendations

1. **Use Level 4 prompting** for most models (7 of 9 peak here)
2. **OpenAI models respond best** to security prompting (+3.22pp average)
3. **Ollama models benefit too** (4 of 5 improve, contrary to old claims)
4. **Anthropic is mixed** - Claude Sonnet improves (+2.70pp), Opus stays flat (-0.32pp)
5. **Avoid Level 5 self-review** - causes regression in many models

---

## Data Files

- Individual reports: `reports/*_level*.json`
- Total configurations: 9 models × 5 levels = 45 test runs
- Tests per configuration: 730 prompts
- Total security tests: 32,850

---

**Critical Correction:** The previous claim that "Ollama models regress with security prompting" was completely backwards. The actual data shows 80% of Ollama models improve with security prompting, and OpenAI (not Anthropic) shows the strongest response to security guidance.
