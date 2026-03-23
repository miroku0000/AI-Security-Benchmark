# Whitepaper Update Status

## Current Situation

The whitepaper needs to be updated to reflect:
1. **Reduction from 141 to 140 prompts** (rust_013 removed for fairness)
2. **New scoring scale**: 346 points max (was 208) due to multi-language prompts
3. **Claude Code, Codex, and Cursor results** from manual testing
4. **Temperature study with 140 prompts** (76 configurations)
5. **All baseline model statistics with 140 prompts**

## What Has Changed

### Prompts
- **Before**: 141 prompts including rust_013 (XXE in Rust)
- **After**: 140 prompts (rust_013 removed due to Claude safety filter unfairness)
- **Reason**: See RUST_013_REMOVAL_EXPLANATION.md

### Scoring
- **Old**: 208 points maximum (66 prompts, mostly Python/JavaScript)
- **New**: 346 points maximum (140 prompts, multi-language including Rust, C++, C#, Go, Java)
- **Languages**: Python, JavaScript, Rust, C++, C#, Go, Java (7 languages total)

### Reports Being Regenerated

**Baseline (24 models × 140 prompts)**:
- Running: PID 53800
- Status: In progress (codellama completed: 185/346 = 53.5%)
- Location: `reports/*_208point_20260322.*`

**Temperature Study (76 configurations × 140 prompts)**:
- Running: PID 54024
- Status: In progress
- Location: `reports/*_temp*_208point_20260322.*`

## Available Data

### Manual Testing Results (OLD 208-point scale, 141 prompts)

**Claude Code** (Sonnet 4.5 via Claude Code CLI):
- Score: 125/222 actual points (56.31% of possible)
- Completed: 79/141 prompts (many failures due to multilanguage limitations)
- Secure: 33 | Partial: 15 | Vulnerable: 33
- Vulnerability Rate: 41.8%
- **Note**: Limited language support, many "unsupported language" errors

**Codex (GPT-4o via Codex.app)**:
- Score: 250/292 actual points (85.62% of possible)
- Completed: 111/141 prompts
- Secure: 88 | Partial: 5 | Vulnerable: 21
- Vulnerability Rate: 18.9%
- **Best performer** among manually tested tools

**Cursor** (Claude Sonnet 3.5):
- Score: 199/348 actual points (57.18% of possible)
- Completed: 141/141 prompts
- Secure: 63 | Partial: 27 | Vulnerable: 56
- Vulnerability Rate: 39.7%

### Temperature Study (Being Regenerated with 140 prompts)

**Original findings (141 prompts)**:
- StarCoder2: 17.3pp variation (63.5% → 80.8%)
- Highest security: StarCoder2 @ temp 1.0 (80.8%)
- Temperature matters as much as model selection
- Code-specialized models 2× more temperature-sensitive

**Status**: All being regenerated with 140 prompts to ensure fairness

## Whitepaper Sections That Need Updates

### 1. Abstract
- [x] Change "66 prompts" → "140 prompts"
- [ ] Update "208-point maximum" → "346-point maximum"
- [ ] Update average security score (was 53.6%)
- [ ] Update vulnerability rate (was 38.9%)
- [ ] Update model count (23 → includes Claude Code, Codex, Cursor?)
- [ ] Add note about rust_013 removal

### 2. Introduction
- [ ] Update prompt count: 66 → 140
- [ ] Mention multi-language expansion
- [ ] Reference fairness considerations (rust_013 removal)

### 3. Methodology
- [ ] Update Section 3.2: 66 → 140 prompts, 7 languages
- [ ] Update Section 3.3: Add new languages (Rust, C++, C#, Go, Java)
- [ ] Update Section 3.4: 208 → 346 max score
- [ ] Update Section 3.5: Add Claude Code, Codex, Cursor to model list
- [ ] Add explanation of rust_013 removal

### 4. Results
- [ ] Complete rewrite with new 140-prompt data
- [ ] Add dedicated section for IDE/tool testing (Claude Code, Codex, Cursor)
- [ ] Update all model rankings with 346-point scale
- [ ] Update category analysis
- [ ] Update temperature study findings

### 5. Discussion
- [ ] Update statistics throughout
- [ ] Add discussion of IDE tool results
- [ ] Discuss rust_013 removal and fairness implications

## Action Plan

### Phase 1: Wait for Report Generation ✓
- Baseline reports: Running
- Temperature reports: Running
- ETA: Unknown (check with `ps aux | grep auto_benchmark`)

### Phase 2: Extract New Statistics
Once reports complete:
```bash
# Extract baseline model scores
python3 extract_baseline_stats.py > baseline_140prompts.txt

# Extract temperature study results
python3 extract_temperature_stats.py > temperature_140prompts.txt

# Get Claude Code, Codex, Cursor stats from OLD reports
# (They're already done, just need to document they use 141 prompts)
```

### Phase 3: Update Whitepaper
1. Update abstract with new totals
2. Update methodology section
3. Add new "IDE Tools & Coding Assistants" section
4. Update all result tables
5. Update temperature study section
6. Add rust_013 removal explanation
7. Update conclusion

### Phase 4: Verify Accuracy
- [ ] Check all numbers add up
- [ ] Verify model rankings
- [ ] Cross-check with JSON reports
- [ ] Ensure temperature study stats are accurate

## Key Points for Whitepaper

### Claude Code Performance
- Tested via Claude Code CLI
- Limited to languages CLI supports (Python, JavaScript primarily)
- Many prompts failed with "unsupported language"
- Of completed prompts: 56.3% security score
- Shows Claude Sonnet 4.5 performs worse via CLI than direct API

### Codex (GPT-4o) Performance
- **Best manual tool tested**: 85.6% security score
- Completed 111/141 prompts
- Only 18.9% vulnerability rate
- Significantly outperforms base GPT-4o API testing
- **Key finding**: IDE context may improve security outcomes

### Cursor Performance
- Full 141/141 prompt completion
- 57.2% security score
- 39.7% vulnerability rate
- Uses Claude Sonnet 3.5 internally
- Similar performance to base Claude Sonnet API

### Temperature Study Key Finding
**Configuration matters as much as model selection.**
- Up to 17.3pp variation by temperature alone
- StarCoder2 @ temp 1.0 achieves highest security (80.8%)
- Must document temperature as security parameter
- Code-specialized models most sensitive

## Status Summary

- ✅ rust_013 removed from all directories
- ✅ prompts.yaml updated (140 prompts)
- ✅ Documentation created (RUST_013_REMOVAL_EXPLANATION.md)
- ✅ TEMPERATURE_STUDY_COMPLETE.md updated
- 🔄 Baseline reports regenerating (24 models × 140 prompts)
- 🔄 Temperature reports regenerating (76 configs × 140 prompts)
- ⏳ Whitepaper update pending report completion

## Next Steps

1. **Monitor report generation**:
   ```bash
   tail -f auto_benchmark_140prompts.log
   tail -f regenerate_temperature_reports.log
   ```

2. **When complete, extract statistics**:
   - Collect all baseline scores
   - Collect all temperature study scores
   - Calculate averages and rankings

3. **Update whitepaper systematically**:
   - Section by section
   - Verify every number
   - Add new sections for IDE tools

4. **Final review**:
   - Accuracy check
   - Consistency check
   - Grammar and clarity

---
Updated: March 22, 2026 20:40
Status: Reports regenerating, whitepaper update pending
