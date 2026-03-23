# Codex.app Security Study - Fixes Applied

**Date**: 2026-03-23

---

## Issues Found and Fixed

### 1. Incorrect File Extensions (CRITICAL)

**Problem**: Both test scripts were generating `.txt` files for C++ and C# code instead of `.cpp` and `.cs`.

**Impact**: 
- Security testing framework couldn't analyze 30 files in no-skill version
- Initial analysis showed only 78.6% completion (110/140) for no-skill
- Made skill appear to have 100% vs 78.6% advantage when both had 140 files

**Root Cause**: `get_file_extension()` function only recognized 6 languages, defaulted to `.txt`

**Fix Applied**:
```python
def get_file_extension(language: str) -> str:
    """Get file extension for language."""
    extensions = {
        'python': 'py',
        'javascript': 'js',
        'typescript': 'ts',
        'java': 'java',
        'go': 'go',
        'rust': 'rs',
        'cpp': 'cpp',      # ADDED
        'c++': 'cpp',      # ADDED
        'csharp': 'cs',    # ADDED
        'c#': 'cs',        # ADDED
    }
    return extensions.get(language.lower(), 'txt')  # CHANGED: added .lower()
```

**Files Modified**:
- `scripts/test_codex_app.py` (no-skill version)
- `scripts/test_codex_app_secure.py` (security-skill version)

**Manual Cleanup**:
- Renamed 30 .txt files in `output/codex-app-no-skill/` (15 C++, 15 C#)
- Renamed 30 .txt files in `output/codex-app-security-skill/` (15 C++, 15 C#)

---

### 2. Results JSON Cluttering Output Directories

**Problem**: Generation results JSON files were saved in the same directory as generated code files.

**Impact**: 
- Confused file counts (141 files instead of 140)
- Mixed metadata with code files

**Fix Applied**:
```python
# OLD: results_file = output_dir / f'codex-app-..._generation_results.json'

# NEW: Save to reports/ directory
reports_dir = Path('reports')
reports_dir.mkdir(parents=True, exist_ok=True)
results_file = reports_dir / f'codex-app-..._generation_results.json'
```

**Files Modified**:
- `scripts/test_codex_app.py`
- `scripts/test_codex_app_secure.py`

**Manual Cleanup**:
- Removed `codex-app-security-skill-gpt-5.4_generation_results.json` from output directory

---

### 3. Incorrect Initial Analysis

**Problem**: Compared no-skill (110 analyzed) vs security-skill (140 analyzed) leading to wrong conclusions.

**Initial (WRONG) Results**:
- Security improvement: +0.5%
- Completion: 78.6% vs 100%
- Vulnerable: 14.5% vs 15.0% (skill was WORSE)

**Corrected Results** (after fixing extensions):
- Security improvement: **+2.6%**
- Completion: **100% vs 100%** (both complete)
- Vulnerable: **17.1% vs 15.0%** (skill is BETTER - 12.5% fewer vulnerabilities)

---

## Current State

### Both Versions Now Have:
- ✅ 140 files with correct extensions
- ✅ 100% completion rate (140/140 analyzed)
- ✅ Clean separation of code and metadata
- ✅ Proper apples-to-apples comparison

### Final Comparison:

| Metric | No-Skill | Security-Skill | Improvement |
|--------|----------|----------------|-------------|
| **Score** | 302/350 (86.3%) | 311/350 (88.9%) | **+2.6%** |
| **Secure** | 115/140 (82.1%) | 120/140 (85.7%) | **+3.6%** |
| **Vulnerable** | 24/140 (17.1%) | 21/140 (15.0%) | **-12.5%** |

---

## Prevention

### For Future Test Runs:

1. **Always add new languages to extension mapping** before running tests
2. **Check file counts** after generation: `ls output/dir/*.{py,js,java,cs,cpp,go,rs} | wc -l`
3. **Verify extensions**: `ls output/dir/*.txt` should return "no matches"
4. **Compare completion rates** - both versions should have same total tests
5. **Keep metadata separate** - JSON results in `reports/`, code in `output/`

### Updated Scripts Now Handle:
- 10 file extensions (py, js, ts, java, go, rs, cpp, cs)
- Case-insensitive language matching
- Results saved to reports/ directory
- No .txt files for code (only for truly unknown languages)

---

## Lessons Learned

1. **File extension mapping is critical** - 21% of test files were affected
2. **Initial analysis can be misleading** - wrong conclusion reversed after fix
3. **Manual verification essential** - user caught the discrepancy
4. **Test framework assumptions matter** - ".txt" files weren't analyzed
5. **Apples-to-apples comparison required** - can't compare 110 vs 140 tests

---

**Conclusion**: The security-best-practices skill provides **meaningful +2.6% security improvement** and **12.5% reduction in vulnerabilities**. Both test versions now generate 140 properly-formatted files for accurate comparison.
