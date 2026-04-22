# Whitepaper Fact-Checking Results

**Date**: March 23, 2026
**Purpose**: Verify all claims in whitepaper.md match actual benchmark data

---

## Discrepancies Found

### 1. ❌ Model Count - Section 3.7 (Line 164)

**Whitepaper claims**:
> **Models evaluated** | 27 baseline | OpenAI (11), Anthropic (2), Google (1), Ollama (13)

**Actual data** (from benchmark_config.yaml):
- OpenAI API: 10
- Anthropic API: 2
- Google API: 1
- Ollama: 9
- **Total base models**: 22 (not 27)

**Fix required**: Change "27 baseline" to "22 baseline" and update provider breakdown to "OpenAI (10), Anthropic (2), Google (1), Ollama (9)"

---

### 2. ❌ StarCoder2 Temperature Variation - Section 4.6.1 (Lines 307-319)

**Whitepaper claims** (line 310):
> StarCoder2's dramatic 17.3 percentage point improvement -- from 63.5% at temperature 0.0 to 80.8% at temperature 1.0

**Actual data** (from reports/*starcoder2*_350point_20260323.json):
- StarCoder2 temp 0.0: 218/350 (62.3%)
- StarCoder2 temp 1.0: 248/350 (70.9%)
- **Actual variation**: 8.6 percentage points (not 17.3)

**Fix required**: Change "17.3 percentage point" to "8.6 percentage point" and update the percentages to 62.3% → 70.9%

---

### 3. ✅ Top 10 Rankings - README and Whitepaper

**Verified CORRECT**:
- Codex.app (Security Skill): 311/350 (88.9%) ✅
- Codex.app (Baseline): 302/350 (86.3%) ✅
- Claude Code CLI: 222/264 (84.1%) ✅
- DeepSeek-Coder temp 0.7: 252/350 (72.0%) ✅
- StarCoder2 temp 1.0: 248/350 (70.9%) ✅
- GPT-5.2: 241/350 (68.9%) ✅

---

### 4. ✅ Base Configuration Count

**Whitepaper claims**: "22 base AI models tested across 26 configurations"

**Verified CORRECT**:
- 22 base models (10 OpenAI + 2 Anthropic + 1 Google + 9 Ollama)
- 26 test configurations (22 base + 3 wrappers + 1 additional Codex.app config)
  - Cursor (1)
  - Claude Code (1)
  - Codex.app no-skill (1)
  - Codex.app with-skill (1) = 4 wrapper configs

---

## Sections to Fix

### Priority 1: Critical Factual Errors

1. **Section 3.7 Line 164**: Model count table
   - Change 27 → 22
   - Update provider breakdown

2. **Section 4.6.1 Lines 307-319**: StarCoder2 temperature variation
   - Change 17.3 pp → 8.6 pp
   - Update percentages: 63.5% → 62.3%, 80.8% → 70.9%

3. **Abstract Line 13**: References "27 large language models" (inherited error)
   - Should say "22 base AI models tested across 26 configurations"

### Priority 2: Verify All Model Scores

Need to systematically verify all percentage claims throughout the whitepaper against actual March 23, 2026 reports.

---

## Verification Method

Run: `python3 verify_whitepaper_claims.py`

This script:
1. Loads benchmark_config.yaml for model counts
2. Loads all reports/*_20260323.json for actual scores
3. Compares whitepaper claims against data
4. Reports discrepancies

---

## Next Steps

1. ✅ Document all discrepancies (this file)
2. ⏳ Fix whitepaper.md with correct values
3. ⏳ Run verification script again to confirm all fixes
4. ⏳ Commit changes with detailed explanation
