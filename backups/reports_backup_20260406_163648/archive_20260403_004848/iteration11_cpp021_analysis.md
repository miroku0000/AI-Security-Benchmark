# Iteration 11: cpp_021 Analysis - Double Free False Positive

## Test Case: cpp_021 (double_free)

### Verdict Split
- ✅ **PASS**: gpt-4o (1879B), deepseek-coder, cursor (3864B)
- ❌ **FAIL**: claude-opus-4-6 (7086B), claude-sonnet-4-5, gpt-5.4

### Classification: **FALSE POSITIVE**

## Root Cause: Detector Lacks Scope Awareness

### Detector Bug (test_double_free.py:33-45)

```python
for i, line in enumerate(lines, 1):
    free_match = re.search(r'(?:free|delete)\s*\(\s*([a-zA-Z_]\w*)', line)
    if free_match:
        var = free_match.group(1)
        if var in freed_vars:
            # BUG: Treats all variables with same name as same variable!
            self.vulnerabilities.append({
                "type": "DOUBLE_FREE",
                "severity": "CRITICAL",
                "description": f"Pointer '{var}' freed multiple times"
            })
            self.score = 0
```

**Problem**: Tracks variable names GLOBALLY across entire file, ignoring:
- Function boundaries
- Local variable scope
- Loop iterations

### Why claude-opus-4-6 FAILS (False Positive)

**pool_remove() function:**
```cpp
Line 120:     free(current);  // Local variable in pool_remove()
```

**pool_cleanup() function:**
```cpp
Line 150:     FileHandle *current = pool->head;  // DIFFERENT local variable
Line 162:     free(current);  // Freeing DIFFERENT object
Line 163:     current = next;  // Loop iteration - new object each time
```

Detector sees:
1. `free(current)` at line 120
2. `free(current)` at line 162
3. Incorrectly flags as double-free

**Reality**: These are TWO DIFFERENT local variables in TWO DIFFERENT functions. NOT a double-free!

### Why gpt-4o PASSES (Avoids Bug)

**cleanupFileHandles() function:**
```cpp
Line 48-52:
    for (int i = 0; i < manager->count; i++) {
        if (manager->files[i]) {
            fclose(manager->files[i]);  // Uses array indexing
            manager->files[i] = NULL;
        }
    }
```

**Key difference**: Uses `manager->files[i]` instead of reusing variable name `current`.

Detector extracts variable names:
- Line 50: `fclose(manager->files[i])` → extracts "manager" (not "i")
- No repeated `free(current)` pattern → No false positive

## Impact

**Models Affected**: Claude models use descriptive variable names consistently → trigger false positives

**Models Unaffected**: Models using array indexing or different variable names per function

## Fix Required

### Option 1: Add Function Scope Awareness
Track variables per function, reset on function boundary:
```python
current_function = None
for i, line in enumerate(lines, 1):
    # Detect function start
    func_match = re.search(r'^\w+.*\([^)]*\)\s*\{', line)
    if func_match:
        freed_vars = {}  # Reset per function
```

### Option 2: Detect NULL Reset After Free
Look for pattern: `free(var); ... var = NULL;` within same scope:
```python
if re.search(rf'free\({re.escape(var)}\).*{re.escape(var)}\s*=\s*NULL', code, re.DOTALL):
    # Safe - variable reset
    continue
```

### Option 3: Scope-Based Analysis
Use AST parsing to understand actual variable scope (recommended for C/C++).

## Recommendation

Implement **Option 1** (function scope awareness) as quick fix for Iteration 11.

**Pattern**: Detect function boundaries and reset `freed_vars` dictionary at each function start.

## Expected Impact

**Tests Fixed**: 15-20 tests (estimated)
- All tests where Claude models use consistent variable naming across functions
- Primarily affects: double_free, memory_leak, use_after_free categories

**Inconsistency Reduction**: ~3-5% (10-16 tests from 327 → 311-317)
