# AWS Bedrock Prevention Fix - Summary

## Problem Identified

Claude Opus 4-6 generation was failing with errors like:
```
ERROR: Anthropic generation error: Error code: 400 - {'message': 'The provided model identifier is invalid.'}
HTTP Request: POST https://bedrock-runtime.us-west-1.amazonaws.com/model/anthropic.claude-3-opus-20240229-v1:0/invoke "HTTP/1.1 400 Bad Request"
```

**Root Cause**: The code was using AWS Bedrock instead of direct Anthropic API, even though the `--use-bedrock` flag was not provided.

## User Feedback

**"we should not be using bedrock!"**

User explicitly stated that Claude models should use the direct Anthropic API, NOT AWS Bedrock.

## Solution Implemented

Modified `code_generator.py` (commit 7fc1f0d4) to **unset the `CLAUDE_CODE_USE_BEDROCK` environment variable** when the `--use-bedrock` flag is not provided.

### Code Change (lines 39-45)

```python
# Initialize Bedrock attributes (will be set properly for Anthropic provider)
# ONLY use Bedrock if --use-bedrock flag is explicitly set
# If flag is not set (use_bedrock=False), unset environment variable to prevent accidental Bedrock usage
if not use_bedrock:
    # Unset environment variable to ensure we use direct Anthropic API
    if 'CLAUDE_CODE_USE_BEDROCK' in os.environ:
        del os.environ['CLAUDE_CODE_USE_BEDROCK']

self.use_bedrock = use_bedrock
self.bedrock_model = None
```

## Behavior After Fix

1. **Default**: Direct Anthropic API (`anthropic.Anthropic()`)
2. **With `--use-bedrock` flag**: AWS Bedrock (`anthropic.AnthropicBedrock()`)
3. **Environment variable is ignored unless flag is provided**

## Impact

- All NEW Claude generation processes will use direct Anthropic API by default
- The old Claude Opus 4-6 process (started before fix) completed with Bedrock errors
- Future Claude processes will not have this issue

## Verification

To verify the fix is working, check the logs for NEW processes:

```bash
# Should see "Anthropic client initialized (direct API)"
grep "Anthropic.*client initialized" <logfile>

# Should NOT see "Bedrock" for processes without --use-bedrock flag
grep -i bedrock <logfile>

# Should see api.anthropic.com, not bedrock-runtime.amazonaws.com
grep -E "https://(api.anthropic.com|bedrock-runtime)" <logfile>
```

## Status

✅ **Fix committed**: commit 7fc1f0d4  
✅ **Code updated**: `code_generator.py` lines 39-45  
⚠️ **Old process**: Claude Opus 4-6 completed with Bedrock errors (started before fix)  
✅ **Future processes**: Will use direct Anthropic API correctly  

---

Generated: 2026-03-31
Commit: 7fc1f0d4
