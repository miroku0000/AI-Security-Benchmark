# Testing Cursor IDE in the Benchmark

## What is Cursor?

**Cursor** is an AI-powered code editor built on VSCode that integrates various AI models (Claude, GPT-4, etc.). Unlike Claude or GPT-4 which are API-accessible models, Cursor is an IDE that requires manual interaction.

## Important Note

Cursor itself is **not a model** - it's an interface to models. When you use Cursor, you're actually using:
- Claude Opus/Sonnet (if configured for Anthropic)
- GPT-4/GPT-4o (if configured for OpenAI)
- Or other models Cursor supports

**Recommendation**: Instead of testing "Cursor", test the specific model Cursor uses through our API-based benchmark for more consistent results.

## Why Manual Testing is Needed

Cursor doesn't provide a direct API for code generation, so automated benchmarking requires manual code generation followed by automated testing.

## Method 1: Manual Generation (Full Cursor Experience)

This tests how Cursor's IDE features (context awareness, multi-file understanding, etc.) affect code security.

### Steps

1. **Setup Output Directory**
   ```bash
   mkdir -p output/cursor
   ```

2. **Open Cursor IDE**
   - Launch Cursor
   - Configure which AI model to use (Settings → AI Model)
   - Note which model you're using for documentation

3. **Generate Code for Each Prompt**

   Open `prompts/prompts.yaml` and for each of the 66 prompts:

   a. **Copy the prompt text**

   b. **In Cursor, use the AI to generate code**:
      - Press `Cmd+K` (Mac) or `Ctrl+K` (Windows/Linux)
      - Paste the prompt
      - Let Cursor generate the code

   c. **Save the generated code**:
      - Save to `output/cursor/<prompt_id>.<ext>`
      - Example: `output/cursor/sql_001.py`
      - Use `.py` for Python prompts, `.js` for JavaScript

   d. **Important**: Save ONLY the generated code, no extra comments or modifications

4. **Run Security Benchmark**

   Once all 66 files are generated:
   ```bash
   python3 runner.py \
     --code-dir output/cursor \
     --model "cursor-claude-opus" \
     --output reports/cursor_claude_opus_208point.json
   ```

   Replace `cursor-claude-opus` with the actual model Cursor is using:
   - `cursor-claude-opus-4-6`
   - `cursor-gpt-4o`
   - `cursor-claude-sonnet-4-5`

5. **View Results**
   ```bash
   # Results saved to:
   # - reports/cursor_claude_opus_208point.json
   # - reports/cursor_claude_opus_208point.html (if HTML enabled)
   ```

### Tracking Progress

Create a checklist to track which prompts you've completed:

```bash
# Create tracking file
ls prompts/prompts.yaml | grep -E "(sql|xss|path|cmd|auth)" > cursor_progress.txt

# Mark completed as you go
```

## Method 2: Semi-Automated (Cursor with Scripts)

If Cursor supports command-line code generation (check Cursor docs), you could potentially script the generation:

```bash
# Check if Cursor has CLI
cursor --help

# If available, you might be able to do:
# cursor generate --prompt "..." --output file.py
```

**Note**: As of my knowledge cutoff, Cursor doesn't have a documented CLI for code generation. Check latest docs.

## Method 3: Test the Underlying Model Directly (Recommended)

The most consistent approach is to test the specific model that Cursor uses through our existing API integration:

### If Cursor Uses Claude Opus 4.6

```bash
python3 auto_benchmark.py --model claude-opus-4-6 --retries 3
```

### If Cursor Uses GPT-4o

```bash
python3 auto_benchmark.py --model gpt-4o --retries 3
```

### Temperature Testing with Cursor's Model

Test at different temperatures to match Cursor's behavior:

```bash
# Cursor typically uses default temperature (0.2-0.3)
python3 auto_benchmark.py --model claude-opus-4-6 --temperature 0.2 --retries 3

# Test at Cursor's "creative" mode (if higher temp)
python3 auto_benchmark.py --model claude-opus-4-6 --temperature 0.7 --retries 3
```

## Comparing Cursor to Direct API

To understand if Cursor's IDE features affect security:

1. **Generate with Cursor** (Method 1)
2. **Generate with Direct API**:
   ```bash
   python3 auto_benchmark.py --model claude-opus-4-6 --retries 3
   ```
3. **Compare Results**:
   ```bash
   # View both reports
   python3 utils/generate_html_reports.py
   open reports/html/index.html
   ```

This comparison reveals:
- Does Cursor's context awareness improve security?
- Do IDE features lead to different vulnerability patterns?
- Is manual prompting via IDE different from API prompts?

## Expected Time

**Manual Generation** (Method 1):
- 66 prompts × ~2 minutes each = **~2 hours**
- Plus setup time = **2-3 hours total**

**Direct API Testing** (Method 3):
- **~5-10 minutes** (fully automated)

## Limitations of Manual Testing

1. **Human Inconsistency**: How you phrase follow-up questions affects output
2. **IDE Context**: Cursor may use surrounding files as context
3. **Not Reproducible**: Can't easily re-run with exact same conditions
4. **Time Intensive**: Hours instead of minutes
5. **No Temperature Control**: Can't precisely control temperature

## Recommendation

**For research purposes**: Use Method 3 (test Cursor's underlying model via API)
- More consistent
- Fully reproducible
- Supports temperature testing
- Much faster

**For understanding IDE impact**: Use Method 1 (manual generation)
- Tests full Cursor experience
- Includes IDE context features
- Real-world usage pattern

## Which Model Does Cursor Use?

Check in Cursor:
1. Open Cursor Settings (`Cmd+,` or `Ctrl+,`)
2. Search for "AI Model" or "Model"
3. Check which model is selected

Common options:
- **Claude Opus 4** → Use `claude-opus-4-6`
- **Claude Sonnet 4** → Use `claude-sonnet-4-5`
- **GPT-4o** → Use `gpt-4o`
- **GPT-4 Turbo** → Use `gpt-4`

## Example: Full Cursor Test Workflow

```bash
# 1. Check which model Cursor uses (via Cursor settings)
#    Let's say it's Claude Opus 4.6

# 2. Test that model directly at Cursor's typical temperature
python3 auto_benchmark.py --model claude-opus-4-6 --temperature 0.3 --retries 3

# 3. (Optional) Manually generate 5 samples with Cursor for comparison
mkdir -p output/cursor_sample
# Generate: sql_001, xss_001, path_001, cmd_001, auth_001 in Cursor
# Save to output/cursor_sample/

# 4. Compare the 5 samples
python3 runner.py --code-dir output/cursor_sample \
  --model cursor-claude-opus-manual \
  --output reports/cursor_manual_sample.json

# 5. Compare against API results
cat reports/cursor_manual_sample.json
cat reports/claude-opus-4-6_208point_*.json
```

## Summary

| Method | Pros | Cons | Time | Reproducible? |
|--------|------|------|------|---------------|
| **Manual (Cursor IDE)** | Tests full IDE experience | Time-consuming, inconsistent | 2-3 hours | ❌ No |
| **Direct API** | Fast, reproducible, supports temperature | Doesn't test IDE features | 5-10 mins | ✅ Yes |
| **Hybrid** | Best of both worlds | Requires both efforts | 2.5-3 hours | ⚠️ Partial |

**For most research**: Use **Direct API** method (Method 3) to test the model Cursor uses. This gives consistent, reproducible results and supports temperature testing.

**For IDE-specific research**: Use **Manual** method (Method 1) to understand if Cursor's features affect security.
