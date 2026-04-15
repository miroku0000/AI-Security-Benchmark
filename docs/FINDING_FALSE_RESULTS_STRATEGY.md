# Strategy for Finding False Positives and False Negatives

**Based on learnings from:** Manual evaluation iteration (80% accuracy, 3 tests fixed)

---

## Key Insight

**Manual evaluation of small, focused samples >> LLM analysis of large batches**

- Manual review (10 tests): 80% accuracy, $0, 3 fixes
- LLM analysis (100 tests): 50-56% accuracy, $2.50, 0 fixes

---

## Recommended Strategy: Multi-Phase Approach

### Phase 1: Low-Hanging Fruit (False Negatives)

**Focus:** FAIL results that should be PASS

**Why start here:**
- Easier to verify (read code, check if actually vulnerable)
- Smaller sample (243 failures vs 517 passes)
- Higher impact per test (turning FAIL→PASS improves metrics)
- Already found 2 detector issues this way

**Method:**

#### 1.1 Category-Based Sampling

Sample 5-10 failures from EACH vulnerability category:

```bash
python3 -c "
import json
from collections import defaultdict

with open('reports/claude-sonnet-4-5_analysis_fixed.json', 'r') as f:
    data = json.load(f)

# Group failures by category
failures_by_category = defaultdict(list)
for r in data['detailed_results']:
    if r.get('primary_detector_result') == 'FAIL':
        failures_by_category[r['category']].append(r['prompt_id'])

# Print sample from each category
for category, failures in sorted(failures_by_category.items()):
    print(f'{category} ({len(failures)} failures):')
    print(f'  Sample: {failures[:5]}')
    print()
"
```

**Review priority:**
1. Categories with **high failure rates** (likely detector issues)
2. Categories with **recent fixes** (XXE, race_condition - might have related issues)
3. Categories with **complex logic** (easier to have false negatives)

#### 1.2 Edge Case Sampling

Focus on scores exactly at threshold (most ambiguous):

```bash
python3 -c "
import json

with open('reports/claude-sonnet-4-5_analysis_fixed.json', 'r') as f:
    data = json.load(f)

edge_cases = []
for r in data['detailed_results']:
    score = r.get('primary_detector_score', 0)
    max_score = r.get('primary_detector_max_score', 2)

    # Exactly at threshold
    if score == max_score / 2:
        edge_cases.append({
            'id': r['prompt_id'],
            'category': r['category'],
            'result': r.get('primary_detector_result'),
            'score': f'{score}/{max_score}'
        })

print(f'Edge cases (score exactly at threshold): {len(edge_cases)}')
for ec in edge_cases[:10]:
    print(f\"  {ec['id']:20s} | {ec['category']:25s} | {ec['result']:4s} | {ec['score']}\")
"
```

**Why edge cases matter:**
- Score = 1/2 or 0.5/1 → FAIL by narrow margin
- Small detector tweak could flip result
- Often reveal detector logic issues

#### 1.3 Pattern-Based Sampling

Look for patterns in failures:

```bash
python3 -c "
import json
from collections import Counter

with open('reports/claude-sonnet-4-5_analysis_fixed.json', 'r') as f:
    data = json.load(f)

# Find common vulnerability types in failures
vuln_types = []
for r in data['detailed_results']:
    if r.get('primary_detector_result') == 'FAIL':
        for v in r.get('vulnerabilities', []):
            vuln_types.append(v.get('type'))

print('Most common vulnerability types in failures:')
for vtype, count in Counter(vuln_types).most_common(10):
    print(f'  {vtype:40s}: {count:3d}')
"
```

**Use patterns to identify:**
- Detector rules that trigger too often
- Language-specific issues (e.g., all JavaScript fails for X)
- Specific code patterns that confuse detector

---

### Phase 2: Hidden Issues (False Positives)

**Focus:** PASS results that should be FAIL

**Why harder:**
- More PASS cases to review (517 vs 243 failures)
- Need to identify vulnerabilities detector MISSED
- Requires deeper code analysis

**Method:**

#### 2.1 Low-Score Passes (Borderline Cases)

Focus on passes with lowest scores (barely passed):

```bash
python3 -c "
import json

with open('reports/claude-sonnet-4-5_analysis_fixed.json', 'r') as f:
    data = json.load(f)

low_score_passes = []
for r in data['detailed_results']:
    if r.get('primary_detector_result') == 'PASS':
        score = r.get('primary_detector_score', 0)
        max_score = r.get('primary_detector_max_score', 2)

        # Passed but with low score (just above threshold)
        if score == max_score / 2 + 0.5 or score == max_score / 2 + 1:
            low_score_passes.append({
                'id': r['prompt_id'],
                'category': r['category'],
                'score': f'{score}/{max_score}',
                'vulns': len(r.get('vulnerabilities', []))
            })

print(f'Low-score passes (barely passed): {len(low_score_passes)}')
for lsp in sorted(low_score_passes, key=lambda x: x['score'])[:15]:
    print(f\"  {lsp['id']:20s} | {lsp['category']:25s} | {lsp['score']:5s} | {lsp['vulns']} findings\")
"
```

**Review these for:**
- Vulnerabilities detector found but didn't score highly enough
- Mitigations detector over-credited
- Edge cases where vulnerability exists but detector missed it

#### 2.2 Category Success Rate Analysis

Find categories with suspiciously high pass rates:

```bash
python3 -c "
import json
from collections import defaultdict

with open('reports/claude-sonnet-4-5_analysis_fixed.json', 'r') as f:
    data = json.load(f)

# Calculate pass rate by category
category_stats = defaultdict(lambda: {'total': 0, 'pass': 0})
for r in data['detailed_results']:
    cat = r['category']
    category_stats[cat]['total'] += 1
    if r.get('primary_detector_result') == 'PASS':
        category_stats[cat]['pass'] += 1

# Sort by pass rate
results = []
for cat, stats in category_stats.items():
    pass_rate = stats['pass'] / stats['total'] if stats['total'] > 0 else 0
    results.append((cat, stats['total'], stats['pass'], pass_rate))

print('Categories by pass rate (highest first):')
print(f'{\"Category\":30s} | Total | Pass | Rate')
print('-' * 60)
for cat, total, passes, rate in sorted(results, key=lambda x: x[3], reverse=True):
    print(f'{cat:30s} | {total:5d} | {passes:4d} | {rate*100:5.1f}%')
"
```

**Investigate categories with:**
- Very high pass rates (>90%) - detector might be too lenient
- Very low pass rates (<30%) - detector might be too strict
- Outliers compared to similar categories

#### 2.3 Known Vulnerability Pattern Search

Search for known vulnerable patterns in PASS code:

```python
# Example script to find specific patterns
import json
from pathlib import Path

with open('reports/claude-sonnet-4-5_analysis_fixed.json', 'r') as f:
    data = json.load(f)

# Define patterns that should FAIL
SUSPICIOUS_PATTERNS = {
    'sql_injection': [
        r'f"SELECT.*{',  # f-string in SQL
        r'"SELECT.*\+',  # String concatenation in SQL
        r'\.format\(.*SELECT',  # .format() in SQL
    ],
    'xss': [
        r'innerHTML\s*=',  # Direct innerHTML assignment
        r'dangerouslySetInnerHTML',  # React dangerous
        r'\|safe',  # Template |safe filter
    ],
    'command_injection': [
        r'shell=True',  # subprocess with shell=True
        r'eval\(',  # eval() usage
        r'exec\(',  # exec() usage
    ],
}

for r in data['detailed_results']:
    if r.get('primary_detector_result') == 'PASS':
        code_path = r.get('generated_code_path')
        if code_path and Path(code_path).exists():
            code = Path(code_path).read_text()

            # Check for suspicious patterns
            category = r['category']
            if category in SUSPICIOUS_PATTERNS:
                for pattern in SUSPICIOUS_PATTERNS[category]:
                    if re.search(pattern, code):
                        print(f"⚠️ {r['prompt_id']}: PASS but has pattern: {pattern}")
```

---

### Phase 3: Systematic Deep Dive

**Focus:** One category at a time, comprehensive review

**Method:**

For each vulnerability category:

1. **Analyze all failures in category** (5-10 manual reviews)
2. **Identify patterns** (common false negatives)
3. **Fix detector** (targeted improvements)
4. **Verify fixes** (re-run category tests)
5. **Review passes in category** (spot-check for false positives)
6. Move to next category

**Example workflow for SQL Injection:**

```bash
# 1. Extract all SQL injection tests
python3 -c "
import json
with open('reports/claude-sonnet-4-5_analysis_fixed.json', 'r') as f:
    data = json.load(f)

sql_tests = [r for r in data['detailed_results'] if r['category'] == 'sql_injection']
failures = [r for r in sql_tests if r.get('primary_detector_result') == 'FAIL']
passes = [r for r in sql_tests if r.get('primary_detector_result') == 'PASS']

print(f'SQL Injection: {len(sql_tests)} total, {len(failures)} fail, {len(passes)} pass')
print(f'\nSample failures:')
for f in failures[:5]:
    print(f\"  {f['prompt_id']}: {f.get('primary_detector_score', 0)}/{f.get('primary_detector_max_score', 2)}\")
" > reports/refinement/sql_injection_review.txt

# 2. Manual review of failures
# Read code for each failure, identify patterns

# 3. Implement detector fixes

# 4. Re-run analysis
python3 runner.py --code-dir output/claude-sonnet-4-5 \
  --output reports/sql_injection_retest.json \
  --model claude-sonnet-4-5

# 5. Compare results
```

---

## Prioritization Matrix

| Priority | Focus | Effort | Impact | Detection |
|----------|-------|--------|--------|-----------|
| **HIGH** | Category-based false negatives | Low | High | Easy |
| **HIGH** | Edge case failures (score = threshold) | Low | Medium | Easy |
| **MEDIUM** | Pattern-based failures | Medium | High | Medium |
| **MEDIUM** | Low-score passes | Medium | Medium | Medium |
| **LOW** | High pass rate categories | High | Low | Hard |
| **LOW** | Systematic deep dive | Very High | Very High | Easy |

---

## Recommended Execution Plan

### Week 1: Quick Wins (False Negatives)

**Goal:** Find and fix 5-10 more false negatives

**Tasks:**
1. Sample 3-5 failures from each of top 5 failing categories
2. Manually review ~20 total tests
3. Identify 2-3 detector issues
4. Implement fixes
5. Verify improvements

**Expected outcome:** +5-10 tests passing

### Week 2: Edge Cases

**Goal:** Review ambiguous cases

**Tasks:**
1. Identify all edge cases (score exactly at threshold)
2. Review 10-15 edge case failures
3. Determine if threshold should change or detector logic needs update
4. Implement improvements

**Expected outcome:** +3-5 tests passing, better threshold calibration

### Week 3: False Positives (Spot Check)

**Goal:** Ensure we're not missing vulnerabilities

**Tasks:**
1. Sample 10 low-score passes (barely passed)
2. Manually verify code is actually secure
3. Search for known vulnerability patterns in passes
4. If found, tighten detector logic

**Expected outcome:** +0-2 tests failing (previously false positives)

### Week 4: Deep Dive (One Category)

**Goal:** Perfect one category

**Tasks:**
1. Choose category with most failures (e.g., command_injection)
2. Review ALL failures in category (comprehensive)
3. Identify all detector issues
4. Implement comprehensive fixes
5. Review all passes in category

**Expected outcome:** Category expertise, significant improvements

---

## Metrics to Track

### Detector Quality Metrics

```python
# Track these over time
metrics = {
    'overall_pass_rate': 0.68,  # Current
    'false_negative_count': 0,  # Known FNs found
    'false_positive_count': 0,  # Known FPs found
    'detector_fixes_applied': 2,  # XXE, race_condition
    'tests_improved': 3,  # xxe_001, race_001, race_002
}
```

### Category-Specific Metrics

```python
# Per category
category_metrics = {
    'sql_injection': {
        'pass_rate': 0.75,
        'reviewed_failures': 5,
        'false_negatives_found': 1,
        'detector_issues': ['f-string detection'],
    },
    # ...
}
```

---

## Tools to Build

### 1. Failure Sampler

```python
#!/usr/bin/env python3
"""Sample diverse failures for manual review."""

import json
import random
from collections import defaultdict
from pathlib import Path

def sample_failures(analysis_file, sample_per_category=5):
    """Sample N failures from each category."""
    with open(analysis_file, 'r') as f:
        data = json.load(f)

    failures_by_category = defaultdict(list)
    for r in data['detailed_results']:
        if r.get('primary_detector_result') == 'FAIL':
            failures_by_category[r['category']].append(r)

    samples = {}
    for category, failures in failures_by_category.items():
        samples[category] = random.sample(failures,
                                         min(sample_per_category, len(failures)))

    return samples

if __name__ == '__main__':
    samples = sample_failures('reports/claude-sonnet-4-5_analysis_fixed.json')

    print('Sampled failures for manual review:')
    for category, failures in sorted(samples.items()):
        print(f'\n{category}:')
        for f in failures:
            print(f'  - {f["prompt_id"]}')
```

### 2. Pattern Finder

```python
#!/usr/bin/env python3
"""Find specific code patterns in PASS/FAIL tests."""

import json
import re
from pathlib import Path

def find_pattern_in_results(analysis_file, patterns, result_filter='PASS'):
    """Search for patterns in specific result category."""
    with open(analysis_file, 'r') as f:
        data = json.load(f)

    matches = []
    for r in data['detailed_results']:
        if r.get('primary_detector_result') != result_filter:
            continue

        code_path = r.get('generated_code_path')
        if not code_path or not Path(code_path).exists():
            continue

        code = Path(code_path).read_text()

        for pattern_name, pattern in patterns.items():
            if re.search(pattern, code):
                matches.append({
                    'test_id': r['prompt_id'],
                    'category': r['category'],
                    'pattern': pattern_name,
                    'result': result_filter
                })

    return matches
```

### 3. Category Analyzer

```python
#!/usr/bin/env python3
"""Analyze detector performance by category."""

import json
from collections import defaultdict

def analyze_categories(analysis_file):
    """Generate category-level statistics."""
    with open(analysis_file, 'r') as f:
        data = json.load(f)

    stats = defaultdict(lambda: {
        'total': 0,
        'pass': 0,
        'fail': 0,
        'avg_score': 0,
        'scores': []
    })

    for r in data['detailed_results']:
        cat = r['category']
        stats[cat]['total'] += 1

        if r.get('primary_detector_result') == 'PASS':
            stats[cat]['pass'] += 1
        else:
            stats[cat]['fail'] += 1

        score = r.get('primary_detector_score', 0)
        max_score = r.get('primary_detector_max_score', 2)
        normalized_score = score / max_score if max_score > 0 else 0
        stats[cat]['scores'].append(normalized_score)

    # Calculate averages
    for cat in stats:
        scores = stats[cat]['scores']
        stats[cat]['avg_score'] = sum(scores) / len(scores) if scores else 0

    return dict(stats)
```

---

## Red Flags to Watch For

### Detector Issues

1. **All tests in category fail** → Detector too strict
2. **All tests in category pass** → Detector too lenient
3. **Language-specific failure pattern** → Detector doesn't handle language properly
4. **Sudden score drop between similar tests** → Detector inconsistent

### Code Generation Issues

1. **Many passes with LOW scores** → Model generates partial mitigations
2. **Many failures with HIGH scores** → Model generates vulnerable code with good practices
3. **Category-specific patterns** → Model doesn't understand specific vulnerability

---

## Example: Finding Next False Negative

Let me demonstrate the process:

```bash
# 1. Sample 5 failures from command_injection category
python3 -c "
import json
import random

with open('reports/claude-sonnet-4-5_analysis_fixed.json', 'r') as f:
    data = json.load(f)

cmd_failures = [r for r in data['detailed_results']
                if r['category'] == 'command_injection'
                and r.get('primary_detector_result') == 'FAIL']

sample = random.sample(cmd_failures, min(5, len(cmd_failures)))

print('Command Injection Failures to Review:')
for s in sample:
    print(f\"  {s['prompt_id']:20s} | Score: {s.get('primary_detector_score', 0)}/{s.get('primary_detector_max_score', 2)}\")
    print(f\"     File: {s.get('generated_code_path', 'N/A')}\")
"

# 2. Manually read each file
# 3. Identify common patterns in false negatives
# 4. Fix detector
# 5. Verify improvement
```

---

## Success Criteria

**Phase 1 (False Negatives):**
- ✅ Find 2-3 detector issues per iteration
- ✅ Fix 5-10 tests per iteration
- ✅ Improve pass rate by 0.5-1% per iteration

**Phase 2 (False Positives):**
- ✅ Identify 1-2 false positives per category review
- ✅ Tighten detector logic without causing regressions
- ✅ Improve detector confidence

**Phase 3 (Deep Dive):**
- ✅ Achieve >90% confidence in 1 category
- ✅ Document detector design patterns
- ✅ Create category-specific test suite

---

## Conclusion

**Best strategy:** Start with **Phase 1 (Category-Based False Negatives)**

1. Quick wins (high ROI)
2. Build confidence in process
3. Develop detector improvement expertise
4. Then move to harder false positive detection

**Timeline:** 1 month to systematically review all major categories and significantly improve detector quality.
