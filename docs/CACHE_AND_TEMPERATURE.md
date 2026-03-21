# Cache and Temperature Management

## Overview

The benchmark system tracks temperature in both directory structure and cache keys to ensure different temperature runs don't interfere with each other.

## Directory Structure

Generated code is automatically organized by temperature:

```
output/
├── gpt-4o/                    # Default temperature (0.2)
│   ├── sql_001.py
│   ├── xss_001.js
│   └── ...
├── gpt-4o_temp0.5/           # Temperature 0.5
│   ├── sql_001.py
│   ├── xss_001.js
│   └── ...
├── gpt-4o_temp0.7/           # Temperature 0.7
│   ├── sql_001.py
│   ├── xss_001.js
│   └── ...
└── gpt-4o_temp1.0/           # Temperature 1.0
    ├── sql_001.py
    ├── xss_001.js
    └── ...
```

**Naming Convention:**
- Default temperature (0.2): `output/{model}/`
- Non-default temperature: `output/{model}_temp{temperature}/`

## Cache Keys

Cache entries are keyed by model, temperature, and prompt ID:

```
Default temperature (0.2):
  gpt-4o::sql_001
  gpt-4o::xss_001

Temperature 0.7:
  gpt-4o::temp0.7::sql_001
  gpt-4o::temp0.7::xss_001

Temperature 1.0:
  gpt-4o::temp1.0::sql_001
  gpt-4o::temp1.0::xss_001
```

This ensures that:
- Different temperatures are cached separately
- Re-running at the same temperature uses cached results
- Changing temperature triggers regeneration

## Example Workflow

### 1. Initial Run at Default Temperature

```bash
python3 auto_benchmark.py --model gpt-4o --temperature 0.2
```

**Result:**
- Code generated in: `output/gpt-4o/`
- Cache entries: `gpt-4o::sql_001`, `gpt-4o::xss_001`, etc.
- Report: `reports/gpt-4o_208point_20260320.json`

### 2. Run at Different Temperature

```bash
python3 auto_benchmark.py --model gpt-4o --temperature 0.7
```

**Result:**
- Code generated in: `output/gpt-4o_temp0.7/`
- Cache entries: `gpt-4o::temp0.7::sql_001`, `gpt-4o::temp0.7::xss_001`, etc.
- Report: `reports/gpt-4o_temp0.7_208point_20260320.json`

**Note:** This does NOT reuse cache from temperature 0.2 - it generates new code.

### 3. Re-run at Temperature 0.7

```bash
python3 auto_benchmark.py --model gpt-4o --temperature 0.7
```

**Result:**
- Uses cached results from step 2
- No regeneration needed
- Runs benchmark on existing code

## Cache Validation

The cache checks multiple conditions before reusing results:

1. **Prompt hasn't changed** - Hash of prompt text matches
2. **Temperature matches** - Within 0.001 tolerance
3. **Output file exists** - File at expected path exists
4. **Provider matches** - Same API/local provider

If any condition fails, code is regenerated.

## Cache Management Commands

### View Cache Statistics

```bash
python3 cache_manager.py --stats
```

Shows:
- Total cached entries
- Models cached
- Temperature variants
- Success/failure rates

### List Cached Entries

```bash
# All entries
python3 cache_manager.py --list

# Specific model
python3 cache_manager.py --list --model gpt-4o
```

### Clear Cache

```bash
# Clear all cache
python3 cache_manager.py --clear

# Clear specific model (all temperatures)
python3 cache_manager.py --clear-model gpt-4o

# Clear specific entry
python3 cache_manager.py --invalidate gpt-4o sql_001
```

## Force Regeneration

### Ignore Cache but Update It

```bash
python3 auto_benchmark.py --model gpt-4o --temperature 0.7 --force-regenerate
```

- Regenerates code even if cached
- Updates cache with new results
- Useful for testing prompt changes

### Disable Cache Completely

```bash
python3 auto_benchmark.py --model gpt-4o --temperature 0.7 --no-cache
```

- Regenerates all code
- Does NOT update cache
- Useful for one-off experiments

## Temperature vs Cache Efficiency

### Caching Behavior

| Temperature | Cache Efficiency | Notes |
|-------------|------------------|-------|
| 0.0 | High | Deterministic - same input → same output |
| 0.2 (default) | High | Low randomness, fairly consistent |
| 0.5 | Medium | Some variation, still useful to cache |
| 0.7 | Medium | More variation, cache prevents unnecessary API calls |
| 1.0 | Low | High randomness, but cache still useful for exact reruns |

**Even at high temperatures**, caching is valuable because:
- Avoids redundant API costs
- Preserves specific generations for comparison
- Speeds up re-running benchmarks

## Common Scenarios

### Scenario 1: Temperature Study

Run same model at multiple temperatures:

```bash
for temp in 0.2 0.5 0.7 1.0; do
  python3 auto_benchmark.py --model gpt-4o --temperature $temp
done
```

**Result:**
- 4 separate output directories
- 4 separate cache key sets
- 4 separate reports
- No interference between runs

### Scenario 2: Update Prompts

After modifying `prompts/prompts.yaml`:

```bash
# Force regenerate with new prompts
python3 auto_benchmark.py --model gpt-4o --temperature 0.7 --force-regenerate
```

Cache detects prompt hash change and regenerates automatically.

### Scenario 3: Re-test Existing Code

You have generated code but want to re-run security tests:

```bash
python3 runner.py --code-dir output/gpt-4o_temp0.7 \
  --model gpt-4o --temperature 0.7 \
  --output reports/retest.json
```

## Cache File Location

Cache is stored in: `.generation_cache.json`

**Format:**
```json
{
  "gpt-4o::sql_001": {
    "model": "gpt-4o",
    "temperature": 0.2,
    "prompt_hash": "abc123...",
    "output_file": "output/gpt-4o/sql_001.py",
    "generated_at": "2026-03-20T10:30:00"
  },
  "gpt-4o::temp0.7::sql_001": {
    "model": "gpt-4o",
    "temperature": 0.7,
    "prompt_hash": "abc123...",
    "output_file": "output/gpt-4o_temp0.7/sql_001.py",
    "generated_at": "2026-03-20T11:45:00"
  }
}
```

## Best Practices

1. **Use default temperature (0.2) for primary benchmarks**
   - Most consistent results
   - Best cache efficiency
   - Standard for comparisons

2. **Use different temperatures for research**
   - Investigate temperature impact on security
   - Compare vulnerability patterns
   - Study model behavior

3. **Don't mix temperatures when comparing models**
   - Compare gpt-4o@0.2 vs claude@0.2
   - NOT gpt-4o@0.7 vs claude@0.2

4. **Force regenerate after prompt changes**
   - Ensures all models use same prompts
   - Maintains fair comparison

5. **Keep cache for reproducibility**
   - Preserves exact generation results
   - Enables re-running benchmarks quickly
   - Documents when code was generated

## Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| "Will regenerate" every time | Cache key mismatch | Check temperature parameter consistency |
| Wrong directory used | Temperature not in command | Specify `--temperature` explicitly |
| Old results after prompt change | Cache not invalidated | Use `--force-regenerate` |
| Disk space filling up | Many temperature variants | Clear unused temperature variants from cache |
| Cannot find generated code | Wrong directory path | Check `output/{model}_temp{X}/` exists |

## References

- Temperature testing guide: [TEMPERATURE_TESTING.md](TEMPERATURE_TESTING.md)
- Main README: [../README.md](../README.md)
- Cache manager: [../cache_manager.py](../cache_manager.py)
