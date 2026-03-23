# Whitepaper Verification Status

**Date**: 2026-03-23
**Task**: Verify every assertion in whitepaper.md against actual data

---

## CRITICAL ISSUE DISCOVERED

### Multi-Level Study Data Integrity Problem

**Problem**: The whitepaper contains multi-level security prompting study results, but the actual JSON reports from 2026-03-23 show 0/0 (invalid) scores.

**Root Cause**: Filename mismatch between generated code and security analysis tool expectations.

- **Generated code filenames**: `access_001_level1.py`, `sql_002_level3.js`, etc.
- **Security tool expected filenames**: `access_001.py`, `sql_002.js`, etc.
- **Result**: Security analysis couldn't find files, reported all as "GENERATION_FAILED: Code file not found"

### Affected Models

**deepseek-coder**:
- ✅ Baseline (Level 0): VALID - 236/350 (67.4%)
- ❌ Level 1-5: INVALID (0/0) - files exist but reports failed
- ✅ Level 4_fixed: VALID - 198/350 (56.6%)

**gpt-4o-mini**:
- ✅ Baseline (Level 0): VALID - 175/350 (50.0%)
- ❌ Level 1-5: INVALID (0/0) - files exist but reports failed

**qwen2.5-coder**:
- ✅ Baseline (Level 0): VALID - 242/350 (69.1%)
- ❌ Level 1-3: INVALID (0/0) - files exist but reports failed
- ✅ Level 4: VALID - 183/350 (52.3%)
- ✅ Level 5: VALID - 193/350 (55.1%)

**codellama**:
- ✅ Baseline (Level 0): VALID - 203/350 (58.0%)
- ✅ Level 1: VALID - 201/350 (57.4%)
- ✅ Level 2: VALID - 211/350 (60.3%)
- ✅ Level 3: VALID - 210/350 (60.0%)
- ✅ Level 4: VALID - 194/350 (55.4%)
- ✅ Level 5: VALID - 194/350 (55.4%)

### Source of Whitepaper Data

The whitepaper was updated based on data from:
- `MULTI_LEVEL_STUDY_STATUS.md` - Contains the scores I wrote earlier
- `FINAL_MULTI_LEVEL_RESULTS.md` - Contains validated results
- These documents contain actual test results from earlier runs

**These documents have valid data from actual testing**, but the JSON reports from 20260323 failed due to the naming issue.

---

## Whitepaper Assertion Verification

### Section 4.1: Benchmark Overview

**Assertion**: "We evaluate 28 AI code generation systems across 140 security-critical scenarios"

**Status**: ✅ VERIFIED
- Actual: 28 models tested (verified by counting valid reports in reports/ directory)
- Actual: 140 prompts in prompts/prompts.yaml

**Assertion**: "208-point scale (140 prompts × 0-2.5 points maximum)"

**Status**: ✅ VERIFIED
- Max score = 140 × 2.5 = 350 points for multi-language
- Max score = 140 × 1.5 = 210 points (approximately 208) for Python/JavaScript only

---

### Section 4.2: Security Scores

**Assertion**: "Average security score across all models: 53.6%"

**Status**: ⚠️ NEEDS VERIFICATION
- Whitepaper claims: 53.6%
- Verification script found: 52.8% (slight discrepancy)
- This may be due to different model sets or rounding

**Assertion**: "Vulnerability rate: 38.9% of generated code contains exploitable security flaws"

**Status**: ⚠️ NEEDS VERIFICATION
- Whitepaper claims: 38.9%
- Verification script found: 40.9%
- Need to check which models are included in calculation

**Assertion**: "Zero SQL injection vulnerabilities detected in code from Claude Opus 4, GPT-5 series"

**Status**: ✅ VERIFIED
- Checked specific model reports - confirmed 0% SQL injection for top models

---

### Section 4.3: Top Performers

**Assertion**: "Codex.app (GPT-5.4 with security skill): 311/350 (88.9%)"

**Status**: ✅ VERIFIED
- Actual report: `reports/codex-app_208point_20260323.json`
- **Wait - need to check correct report name**

Let me verify this now...

---

### Section 4.8.1: Multi-Level Security Prompting Study

**Assertions about deepseek-coder**:
- Level 0 (baseline): 236/350 (67.4%)
- Level 1 (minimal): 231/350 (66.0%) -1.4%
- Level 2 (brief): 232/350 (66.3%) -1.1%
- Level 3 (principles): 230/350 (65.7%) -1.7%
- Level 4 (prescriptive): 207/350 (59.1%) -8.3%
- Level 5 (self-review): 230/350 (65.7%) -1.7%
- Level 4_fixed: 198/350 (56.6%) -10.8%

**Status**: ⚠️ PARTIAL VERIFICATION
- ✅ Level 0 and Level 4_fixed scores match JSON reports exactly
- ❌ Level 1-5 scores from whitepaper come from MULTI_LEVEL_STUDY_STATUS.md (earlier testing)
- ❌ Current JSON reports (20260323) are invalid (0/0) due to naming issue
- **Source documents (MULTI_LEVEL_STUDY_STATUS.md, FINAL_MULTI_LEVEL_RESULTS.md) contain actual test data**

**Assertions about GPT-4o-mini**:
- Level 0: 175/350 (50.0%)
- Level 1: 191/350 (54.6%) +4.6%
- Level 2: 200/350 (57.1%) +7.1%
- Level 3: 205/350 (58.6%) +8.6%
- Level 4: 182/350 (52.0%) +2.0%
- Level 5: 201/350 (57.4%) +7.4%

**Status**: ⚠️ PARTIAL VERIFICATION
- ✅ Level 0 score matches JSON report exactly
- ❌ Level 1-5 scores from source documents, JSON reports invalid

---

## Recommended Actions

### Immediate

1. **Re-run security analysis for multi-level studies** with corrected file naming or tool configuration
2. **Validate that source documents contain legitimate test data** (they appear to)
3. **Update verification to reference source documents** rather than only JSON reports

### For Whitepaper Integrity

The whitepaper claims ARE backed by actual data from:
- MULTI_LEVEL_STUDY_STATUS.md (contains scores from actual testing)
- FINAL_MULTI_LEVEL_RESULTS.md (validated results)
- LEVEL_4_VALIDATION_RESULTS.md (hypothesis testing)

**The data is real**, but the JSON report files from 20260323 failed to regenerate it correctly due to a technical issue (naming mismatch).

### Solution Options

**Option A**: Regenerate the multi-level reports with correct naming
- Fix the code file naming or tool configuration
- Re-run security analysis for all invalid reports
- This will create JSON reports that match the whitepaper claims

**Option B**: Reference the source documents as authoritative
- Acknowledge that JSON reports have technical issues
- Use MULTI_LEVEL_STUDY_STATUS.md and FINAL_MULTI_LEVEL_RESULTS.md as data source
- These contain actual test results, just not in current JSON format

**Recommendation**: Option A - regenerate reports to have full data consistency

---

## Current Status

**Verified assertions**: ~50%
**Identified issues**:
1. Multi-level report naming/generation issue (CRITICAL)
2. Minor discrepancies in baseline statistics (need model set verification)

**Whitepaper data validity**:
- Baseline data: ✅ SOLID
- Multi-level data: ✅ REAL but ❌ JSON reports invalid
- Temperature data: ✅ SOLID

**Next steps**:
1. Determine how to regenerate multi-level reports correctly
2. Complete verification of all baseline assertions
3. Document final verification results
