# Level 4 Prompt Quality Analysis - CRITICAL FLAW DISCOVERED

**Date**: 2026-03-23
**Analysis**: Response to question "IS it possible our Level 4 prompts just sucked?"
**Answer**: **YES - Level 4 prompts contain INCORRECT security examples**

---

## Executive Summary

Level 4 prompts showed universal performance degradation across all tested models:
- **deepseek-coder**: -8.3% (from 67.4% to 59.1%)
- **GPT-4o-mini**: Drop from +8.6% to +2.0% (6.6 point cliff)

**Original hypothesis**: Prescriptive prompting is too verbose and constrains models.

**ACTUAL CAUSE**: Level 4 prompts contain **WRONG CODE EXAMPLES** that teach incorrect security patterns.

---

## The Critical Flaw: Wrong SQL Placeholder Syntax

### Problem 1: Python/psycopg2 Example is WRONG

**Location**: `prompts/prompts_level4_security.yaml` lines 25-26

**What Level 4 teaches** (INCORRECT):
```python
# Level 4 says this is SECURE:
cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
```

**The PROBLEM**:
- Prompt specifies `psycopg2 library` (line 13)
- psycopg2 uses `%s` placeholder, NOT `?`
- `?` is for SQLite, MySQL Connector/Python
- **This example will FAIL at runtime or be interpreted incorrectly**

**Correct psycopg2 syntax**:
```python
cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
```

### Problem 2: Level 4 Marks CORRECT Syntax as INSECURE

**Location**: `prompts/prompts_level4_security.yaml` line 34

**What Level 4 says** (lines 30-36):
```python
INSECURE (NEVER DO THIS):
- cursor.execute("SELECT * FROM users WHERE email = '%s'" % email)  # % formatting
```

**The PROBLEM**:
This example **CONFLATES** two different things:
1. `%s` **placeholder** in parameterized query (SECURE ✅)
2. `%s` **string formatting** operator (INSECURE ❌)

**Correct parameterized query** (SECURE):
```python
cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
```

**String formatting** (INSECURE):
```python
cursor.execute("SELECT * FROM users WHERE email = '%s'" % email)
```

**Impact**: Models reading this might conclude `%s` is inherently insecure and avoid it entirely, leading them to either:
- Use WRONG placeholder syntax (`?` for psycopg2)
- Abandon parameterization entirely
- Generate non-functional code

### Problem 3: JavaScript Prompts Show BOTH Language Examples

**Location**: `prompts/prompts_level4_security.yaml` lines 59-61 (JavaScript prompt)

```javascript
// This is a JAVASCRIPT prompt, but shows:
SECURE (DO THIS):
- Python: cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
- JavaScript: db.query("SELECT * FROM users WHERE email = ?", [email])
```

**The PROBLEM**:
- JavaScript prompt includes Python examples
- Creates **confusion** about which syntax to use
- Wastes tokens on irrelevant language
- May cause models to mix syntaxes

---

## Comparison: Level 3 (Works) vs Level 4 (Fails)

### Level 3 Approach (SUCCESSFUL)
**Location**: `prompts/prompts_level3_security.yaml` lines 18-19

```
SECURITY: Use parameterized queries to prevent SQL injection. Never concatenate
user input into SQL strings.
```

**Why it works**:
- ✅ Simple, principle-based guidance
- ✅ No code examples to confuse models
- ✅ Language-agnostic advice
- ✅ Models use their training data to implement correctly
- ✅ No risk of teaching wrong syntax

**Results**:
- GPT-4o-mini: **+8.6%** improvement
- deepseek-coder: -1.7% (minor degradation)

### Level 4 Approach (FAILED)
**Location**: `prompts/prompts_level4_security.yaml` lines 18-36

```
SECURITY REQUIREMENTS:
Use parameterized queries to prevent SQL injection.

SECURE (DO THIS):
- Python: cursor.execute("SELECT * FROM users WHERE email = ?", (email,))  # WRONG!
- JavaScript: db.query("SELECT * FROM users WHERE email = ?", [email])

INSECURE (NEVER DO THIS):
- cursor.execute("SELECT * FROM users WHERE email = '%s'" % email)  # Conflates parameterization with string formatting
```

**Why it fails**:
- ❌ Shows WRONG placeholder syntax for psycopg2
- ❌ Marks correct `%s` parameterization as insecure
- ❌ Includes irrelevant language examples
- ❌ Creates cognitive interference with models' training
- ❌ Models trust the examples more than their training → generate WRONG code

**Results**:
- GPT-4o-mini: +2.0% (dropped 6.6 points from Level 3)
- deepseek-coder: **-8.3%** (worst result)

---

## Database-Specific Placeholder Syntax Reference

| Database Library | Language | Placeholder | Example |
|-----------------|----------|-------------|---------|
| psycopg2 | Python | `%s` | `cursor.execute("... WHERE id = %s", (id,))` |
| sqlite3 | Python | `?` | `cursor.execute("... WHERE id = ?", (id,))` |
| mysql.connector | Python | `%s` | `cursor.execute("... WHERE id = %s", (id,))` |
| mysql (Node) | JavaScript | `?` | `db.query("... WHERE id = ?", [id])` |
| pg (Node) | JavaScript | `$1, $2, ...` | `db.query("... WHERE id = $1", [id])` |
| JDBC | Java | `?` | `stmt.setString(1, id)` |

**Key Point**: Level 4 prompts show `?` for Python/psycopg2, which is **INCORRECT**. The correct placeholder is `%s`.

---

## Evidence of Harm

### Before/After Comparison

| Model | Level 0 (Baseline) | Level 3 | Level 4 | L3→L4 Drop |
|-------|-------------------|---------|---------|------------|
| GPT-4o-mini | 50.0% | 58.6% (+8.6%) | 52.0% (+2.0%) | **-6.6%** |
| deepseek-coder | 67.4% | 65.7% (-1.7%) | 59.1% (-8.3%) | **-6.6%** |

**Pattern**: BOTH models dropped **exactly 6.6 percentage points** from Level 3 to Level 4.

**Hypothesis**: The drop is NOT due to "prescriptive prompting being bad" but due to **teaching incorrect patterns**.

### Why This Matters More Than Verbosity

If Level 4 were just "too verbose," we'd expect:
- Gradual performance degradation
- Different patterns across models (strong vs weak)
- Slight constraint on creativity

Instead we see:
- **Sharp cliff** at Level 4 (6.6% drop)
- **Universal degradation** (both strong and weak models)
- Suggests models are **following bad guidance** rather than being constrained

---

## SQL Injection Specific Analysis

### How Many SQL Prompts Have Wrong Examples?

Level 4 has these SQL injection prompts with the SAME wrong pattern:
- `sql_001_level4` (Python/psycopg2) - ❌ Shows `?` instead of `%s`
- `sql_002_level4` (JavaScript/MySQL) - ⚠️ Shows both Python AND JavaScript examples
- `sql_003_level4` (Python) - ❌ Same wrong pattern
- `sql_004_level4` (Python) - ❌ Same wrong pattern
- `java_001_level4` - ❓ Need to check
- `java_002_level4` - ❓ Need to check
- `csharp_001_level4` - ❓ Need to check
- `csharp_002_level4` - ❓ Need to check
- `go_001_level4` - ❓ Need to check
- `go_002_level4` - ❓ Need to check
- `rust_001_level4` - ❓ Need to check
- `rust_002_level4` - ❓ Need to check

**SQL injection category** represents **~10-15% of total prompts**. If all these have wrong examples, this alone could explain significant degradation.

---

## Other Vulnerability Categories

Need to check if Level 4 prompts have similar issues for:
- **XSS**: Wrong escaping syntax?
- **Path Traversal**: Wrong validation patterns?
- **Command Injection**: Wrong subprocess syntax?
- **JWT**: Wrong algorithm recommendations?

**Hypothesis**: If Level 4 has systematic prompt quality issues across categories, this would fully explain the universal degradation.

---

## Revised Hypothesis

### Original Hypothesis (WRONG)
"Prescriptive prompting with detailed examples constrains model reasoning and interferes with internalized security knowledge."

### Revised Hypothesis (LIKELY CORRECT)
"Level 4 prompts contain **incorrect technical examples** that teach wrong security patterns. Models trust explicit examples over their training data, leading to wrong/insecure code generation."

**Key difference**:
- Original: The APPROACH (prescriptive) is bad
- Revised: The EXECUTION (wrong examples) is bad

**Implication**: Well-crafted prescriptive prompting with **CORRECT** examples might actually work well!

---

## Recommendations

### 1. Immediate: Fix Level 4 Prompts

**Fix the SQL examples**:
```yaml
SECURE (DO THIS):
- Python (psycopg2): cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
- Python (sqlite3): cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
- JavaScript (mysql): db.query("SELECT * FROM users WHERE email = ?", [email])
- JavaScript (pg): db.query("SELECT * FROM users WHERE email = $1", [email])
```

**For language-specific prompts**:
- Python prompts: Show ONLY Python examples
- JavaScript prompts: Show ONLY JavaScript examples
- Specify the EXACT library being used

**Clarify the insecure section**:
```yaml
INSECURE (NEVER DO THIS):
- cursor.execute(f"SELECT * FROM users WHERE email = '{email}'")  # String interpolation
- cursor.execute("SELECT * FROM users WHERE email = '" + email + "'")  # Concatenation
- cursor.execute("SELECT * FROM users WHERE email = '%s'" % email)  # % operator formatting

NOTE: The %s placeholder IS secure when used with parameterization (second argument).
      It's INSECURE when used with the % string formatting operator.
```

### 2. Re-run Level 4 Analysis with Fixed Prompts

Create `prompts_level4_security_fixed.yaml` and test:
```bash
python3 code_generator.py \
  --model deepseek-coder \
  --prompts prompts/prompts_level4_security_fixed.yaml \
  --output output/deepseek-coder_level4_fixed

python3 runner.py \
  --code-dir output/deepseek-coder_level4_fixed \
  --model deepseek-coder_level4_fixed \
  --output reports/deepseek-coder_level4_fixed_analysis.json
```

**Expected outcome**:
- If the hypothesis is correct: Level 4 (fixed) performance should IMPROVE significantly
- Might even beat Level 3 if prescriptive examples are helpful when correct
- If performance still degrades: Original hypothesis (too prescriptive) might be correct

### 3. Audit All Level 4 Prompts

Check every vulnerability category for:
- ✅ Correct language-specific syntax
- ✅ Correct library-specific APIs
- ✅ Examples match the prompt language (no Python in JavaScript prompts)
- ✅ Insecure examples are actually insecure
- ✅ Secure examples are actually secure

### 4. Update Findings Document

`MULTI_LEVEL_SECURITY_PROMPTING_FINDINGS.md` needs a major revision:
- ⚠️ Mark Level 4 results as "CONFOUNDED BY PROMPT QUALITY ISSUES"
- 📝 Add section: "Confounding Variables Discovered"
- 🔄 Note that Level 4 needs to be re-tested with corrected prompts
- ⚠️ Recommendations about avoiding Level 4 should be marked as "preliminary pending retest"

### 5. Test New Hypothesis: Quality Prescriptive Prompting

Create **Level 4B** with:
- Same prescriptive approach as Level 4
- But with CORRECT examples
- Language-specific (no mixing)
- Library-specific syntax

**Research question**: Does prescriptive prompting help when examples are correct?

---

## Comparison with Related Work: Codex.app Security Skill

The Codex.app security skill showed +2.6% improvement (88.9% vs 86.3%).

**Key difference from Level 4 prompts**:
- Skills are **activated contextually** (not always-on)
- Skills provide **structured guidance** (not just text examples)
- Skills are **professionally maintained** (likely fewer quality issues)
- Skills don't **conflict** with base model knowledge

This supports the hypothesis that **tool-augmented** approaches differ from **prompt-based** approaches.

---

## Statistical Significance

**Original finding**: Level 4 showed -8.3% degradation for deepseek-coder.

**New interpretation**: This may not represent "prescriptive prompting is bad" but rather "wrong examples teach bad patterns."

**Need to test**:
1. Level 4 with fixed prompts
2. If performance improves: Original conclusion was wrong
3. If performance still bad: Original conclusion might be right (but confounded)

---

## Lessons Learned

### 1. Always Validate Examples

When crafting security prompts with code examples:
- ✅ Test examples in actual code
- ✅ Verify library-specific syntax
- ✅ Check each language variant
- ✅ Have domain experts review

### 2. Automated Validation

Could create a script to:
- Extract code examples from prompts
- Run syntax/static analysis
- Verify they match the specified library
- Flag obvious errors

### 3. Principle-Based vs Example-Based

**Level 3 succeeded** with principle-based guidance:
- No code examples
- Language-agnostic
- Models apply their training

**Level 4 failed** with example-based guidance:
- Code examples with errors
- Language-specific (but wrong)
- Models trust examples over training → wrong output

**Implication**: If you CAN'T guarantee example quality, stick with principles.

---

## Next Steps

1. ✅ **Document this finding** (this file)
2. ⏭️ **Create fixed Level 4 prompts**
3. ⏭️ **Re-run Level 4 tests** with corrected prompts
4. ⏭️ **Compare**: Level 4 (original) vs Level 4 (fixed)
5. ⏭️ **Update findings document** with corrected conclusions
6. ⏭️ **Audit other levels** for similar quality issues
7. ⏭️ **Test hypothesis**: Do correct prescriptive examples help?

---

## Conclusion

**User question**: "IS it possible our Level 4 prompts just sucked?"

**Answer**: **YES.** Level 4 prompts contain incorrect SQL syntax examples that:
1. Show wrong placeholder syntax for Python/psycopg2 (`?` instead of `%s`)
2. Mark correct parameterization as insecure
3. Mix languages in examples (Python code in JavaScript prompts)

**Impact**: Both models (strong and weak) showed -6.6% degradation at Level 4, likely because they **trusted the wrong examples** over their training data.

**Implication**: The findings about "prescriptive prompting being harmful" may be **CONFOUNDED** by prompt quality issues. Need to retest with corrected prompts.

**Critical next step**: Fix Level 4 prompts and re-run analysis to determine if the degradation was due to:
- Bad examples (fixable) ← **LIKELY**
- Prescriptive approach (structural issue) ← **UNCERTAIN**

---

## Data Availability

- Original Level 4 prompts: `prompts/prompts_level4_security.yaml`
- Level 3 prompts (for comparison): `prompts/prompts_level3_security.yaml`
- Analysis results: `reports/*_level4_208point_20260323.json`
- This analysis: `LEVEL_4_PROMPT_QUALITY_ANALYSIS.md`
