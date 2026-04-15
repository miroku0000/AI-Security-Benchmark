# Installing the Security Best Practices Skill in Codex.app

This guide explains how to install and verify the Security Best Practices skill in Codex.app for benchmark testing.

## Prerequisites

- **Codex.app installed** from OpenAI
- **Codex.app version**: 0.116.0-alpha.10 or later
- **Active OpenAI account** with Codex access

## Installation Steps

### Method 1: Install from Codex.app UI (Recommended)

1. **Open Codex.app**
   ```bash
   open -a Codex
   ```

2. **Navigate to Skills**
   - Click on the settings icon (⚙️) or use `Cmd+,`
   - Select "Skills" from the left sidebar
   - Or navigate to: `Settings → Skills`

3. **Browse Available Skills**
   - Look for "Security Best Practices" in the skills marketplace
   - The skill should show:
     - **Name**: Security Best Practices
     - **Description**: "Security reviews and secure-by-default guidance"
     - **Supported Languages**: Python, JavaScript/TypeScript, Go

4. **Install the Skill**
   - Click "Install" or "Add" button
   - Wait for installation to complete
   - The skill will appear in your "Installed Skills" list

5. **Verify Installation**
   - Check that "Security Best Practices" appears in your installed skills
   - The skill should be **enabled** by default (toggle should be ON)

### Method 2: Verify Installation via CLI

You can verify the skill is installed by checking the filesystem:

```bash
# Check if skill directory exists
ls -la ~/.codex/skills/

# Should see:
# drwxr-xr-x  6 user  staff  192 Mar 22 22:27 security-best-practices

# Verify skill configuration
cat ~/.codex/skills/security-best-practices/agents/openai.yaml

# Should output:
# interface:
#   display_name: "Security Best Practices"
#   short_description: "Security reviews and secure-by-default guidance"
#   default_prompt: "Review this codebase for security best practices..."
```

### Method 3: Manual Installation (Advanced)

If the skill isn't available in the marketplace, you may need to install it manually:

1. **Download the Skill**
   - Contact OpenAI support or check internal documentation
   - Skills may be distributed as `.codex-skill` packages

2. **Install Manually**
   ```bash
   # Navigate to skills directory
   cd ~/.codex/skills/

   # Create skill directory (if installing from source)
   mkdir -p security-best-practices/agents

   # Copy skill files
   # (Follow OpenAI's skill installation documentation)
   ```

## Verification

### Test the Skill is Working

Run a quick test to ensure the skill responds to explicit invocation:

```bash
# Test with codex CLI
codex exec "Use the security-best-practices skill to review this Python code for SQL injection: def get_user(id): cursor.execute('SELECT * FROM users WHERE id=' + id)"
```

**Expected output**: The skill should identify the SQL injection vulnerability and suggest using parameterized queries.

### Check Skill Status in Python Script

```bash
# Run the installation check
python3 scripts/test_codex_app_secure.py --check

# Should output:
# ✓ Found Codex.app: codex-cli 0.116.0-alpha.10
# ✓ Codex.app is installed and ready
# NOTE: Security Best Practices skill will be triggered via prompt
```

## Skill Behavior

### How the Skill is Triggered

The Security Best Practices skill is **trigger-based**, meaning it only activates when explicitly requested. From the skill documentation (`~/.codex/skills/security-best-practices/SKILL.md`):

> "Trigger only when the user explicitly requests security best practices guidance, a security review/report, or secure-by-default coding help."

### Activation Methods

**✅ CORRECT - Explicit Activation:**
```
"Use the security-best-practices skill to write secure code for..."
"Apply security best practices to..."
"Follow security-best-practices skill guidance for..."
```

**❌ INCORRECT - Does Not Trigger:**
```
"Write secure code..."  # Too vague, won't trigger
"Be careful with SQL injection..."  # Doesn't name the skill
```

### Deactivation

To explicitly disable the skill (important for baseline testing):

```
"Do not use the security-best-practices skill or any other skills."
```

This ensures the baseline test measures pure model capabilities without skill augmentation.

## Benchmark Testing Setup

### Test 1: Baseline (No Skills)

```bash
# Explicitly disables all skills
python3 -u scripts/test_codex_app.py \
  --output-dir output/codex-app-baseline \
  --timeout 120
```

**Prompt includes**: "Do not use the security-best-practices skill or any other skills."

### Test 2: With Security Skill

```bash
# Explicitly enables security skill
python3 -u scripts/test_codex_app_secure.py \
  --output-dir output/codex-app-security-skill \
  --timeout 120
```

**Prompt includes**: "Use the security-best-practices skill to write secure-by-default code..."

### Test 3: Comparison

```bash
# Run security analysis on both
python3 runner.py --code-dir output/codex-app-baseline --model codex-baseline
python3 runner.py --code-dir output/codex-app-security-skill --model codex-security-skill

# Compare results
diff reports/codex-baseline_208point_*.json \
     reports/codex-security-skill_208point_*.json
```

## Supported Languages

According to the skill documentation, security guidance is available for:

- **Python** (general + Django, Flask frameworks)
- **JavaScript/TypeScript** (general + React, Vue, Angular frameworks)
- **Go** (general web security)

**Note**: C#, C++, Java, and Rust may have limited or no skill-specific guidance. The skill may still provide general security advice based on the model's knowledge.

## Troubleshooting

### Codex.app Not Working / Errors

**Problem**: Codex.app CLI returns errors or fails to generate code

**Solution**:
1. **Check your credits**: Visit https://chatgpt.com/codex/settings/usage
   - Codex.app requires active credits to function
   - If you've hit your limit, you'll see: "ERROR: You've hit your usage limit"
   - Purchase more credits or wait for limit reset
2. Verify Codex.app version: `codex --version`
3. Check for known bugs in your Codex version (see Codex CLI Bugs section below)

### Skill Not Found

**Problem**: Skill directory doesn't exist at `~/.codex/skills/security-best-practices/`

**Solution**:
1. Reinstall the skill from Codex.app UI
2. Check if skill is in a different directory
3. Verify Codex.app version supports skills

### Skill Not Activating

**Problem**: Skill doesn't seem to be providing security guidance

**Solution**:
1. Ensure prompt explicitly mentions "security-best-practices skill"
2. Check skill is enabled in Codex.app settings
3. Verify the skill documentation exists:
   ```bash
   cat ~/.codex/skills/security-best-practices/SKILL.md
   ```

### Skill Activating When It Shouldn't

**Problem**: Baseline test is using the skill despite disable instruction

**Solution**:
1. Strengthen the disable instruction in prompt
2. Verify the prompt starts with: "Do not use the security-best-practices skill..."
3. Check Codex.app settings - ensure skill isn't set to "always on"

### Code Generation Timing Out

**Problem**: Skill may add processing time, causing timeouts

**Solution**:
- Increase timeout from 120s to 180s or 240s:
  ```bash
  python3 -u scripts/test_codex_app_secure.py --timeout 180
  ```

## Codex CLI Bugs (v0.116.0-alpha.10)

**CRITICAL**: Codex.app v0.116.0-alpha.10 has severe CLI bugs that may prevent benchmark testing:

### Bug 1: Underscore in Directory Path
- **Symptom**: CLI fails with truncated error: `workdir: /Users/user/Documents/AI_`
- **Cause**: Codex CLI cannot handle underscores in directory names
- **Workaround**: Run from `/tmp` directory (already implemented in test scripts)

### Bug 2: Git Repo Check
- **Symptom**: Error: `Not inside a trusted directory and --skip-git-repo-check was not specified`
- **Cause**: Codex requires git repo or explicit bypass flag
- **Workaround**: Use `--skip-git-repo-check` flag (already implemented in test scripts)

### Bug 3: General CLI Instability
- **Symptom**: Random failures with cryptic error messages ending in "prov"
- **Cause**: Unknown internal CLI error
- **Impact**: 50-95% failure rate on code generation
- **Status**: No known workaround - Codex.app alpha quality not suitable for production use

**Recommendation**: Due to these bugs, we recommend using Claude Code CLI or direct API access for security benchmarking until Codex.app reaches stable release.

## Expected Impact

Based on the skill's design, we expect to see:

### Security Improvements
- ✅ Better input validation
- ✅ Parameterized queries (SQL injection prevention)
- ✅ Output encoding (XSS prevention)
- ✅ Path validation (path traversal prevention)
- ✅ Secure defaults (HTTPS, secure cookies, etc.)

### Potential Trade-offs
- ⚠️ Slightly more verbose code (security comments)
- ⚠️ Longer generation time (5-30s more per prompt)
- ⚠️ May add defensive checks that impact performance

## Whitepaper Documentation

For the whitepaper, document:

1. **Skill Installation Date**: When the skill was installed
2. **Skill Version**: Check `~/.codex/skills/security-best-practices/` for version info
3. **Activation Method**: Explicit prompt-based trigger
4. **Baseline Control**: Explicit skill disabling in baseline tests
5. **Test Methodology**: Two separate test runs with controlled skill state

## References

- **Skill Documentation**: `~/.codex/skills/security-best-practices/SKILL.md`
- **Skill Configuration**: `~/.codex/skills/security-best-practices/agents/openai.yaml`
- **Codex Documentation**: https://openai.com/codex
- **Skills Marketplace**: Available in Codex.app UI

---

**Last Updated**: 2026-03-22
**Codex Version**: 0.116.0-alpha.10
**Skill Version**: security-best-practices (installed via Codex.app)
