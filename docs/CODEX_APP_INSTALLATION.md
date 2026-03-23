# Codex.app Installation Guide

**Official OpenAI Desktop Application**

---

## What is Codex.app?

**Codex.app** is OpenAI's official desktop application for AI-powered code generation. It provides:
- Desktop UI for code generation
- Command-line interface (`codex` CLI)
- Integration with local development workflow
- Uses GPT-5.4 by default (configurable)

**Different from**:
- GitHub Copilot (IDE plugin)
- OpenAI API (programmatic access)
- ChatGPT (web interface)

---

## System Requirements

**Platform**: macOS (primary support)
- macOS 11 (Big Sur) or later
- Apple Silicon (M1/M2/M3) or Intel
- ~500 MB disk space
- Internet connection required

**Other Platforms**:
- Windows: Available (check OpenAI website)
- Linux: Limited/experimental support

---

## Installation Methods

### Method 1: Official Installer (Recommended)

**Download from OpenAI:**

1. Visit: https://openai.com/codex or https://platform.openai.com
2. Look for "Download Codex" or "Desktop App"
3. Download the macOS installer (.dmg or .pkg)
4. Open the installer
5. Drag Codex.app to Applications folder
6. Launch Codex.app from Applications

**Note**: As of March 2026, Codex.app may still be in beta/early access. You may need:
- OpenAI account
- API access (free tier or paid)
- Waitlist approval (if in beta)

### Method 2: Using Homebrew Cask

```bash
# Search for Codex in Homebrew
brew search codex

# If available:
brew install --cask codex-app

# Launch
open -a Codex
```

**Note**: Not all versions may be in Homebrew. Official installer is more reliable.

### Method 3: Direct CLI Installation

If you only need the CLI (not the GUI):

```bash
# Install using curl (if OpenAI provides a CLI-only installer)
curl https://openai.com/install-codex -fsSL | bash

# Or download from GitHub releases (if available)
# Check: https://github.com/openai/codex-cli
```

---

## Post-Installation Setup

### 1. Verify Installation

**Check App Installation:**
```bash
# Verify Codex.app exists
ls -la /Applications/Codex.app

# Check CLI is accessible
/Applications/Codex.app/Contents/Resources/codex --version
```

Expected output:
```
codex-cli 0.116.0-alpha.10
```

**Add CLI to PATH (Optional but Recommended):**
```bash
# Add to your shell profile
echo 'export PATH="/Applications/Codex.app/Contents/Resources:$PATH"' >> ~/.zshrc

# Or create a symlink
sudo ln -s /Applications/Codex.app/Contents/Resources/codex /usr/local/bin/codex

# Reload shell
source ~/.zshrc

# Test
codex --version
```

### 2. Authentication

**Sign in to OpenAI Account:**

```bash
# Launch authentication flow
codex login

# Or open the app GUI
open -a Codex
# Click "Sign In" and follow prompts
```

**You'll need**:
- OpenAI account (free or paid)
- Email verification
- Possibly API key (depends on access tier)

**Check Authentication Status:**
```bash
# Verify you're logged in
codex exec "print hello" --model gpt-5.4

# Should generate code, not show auth error
```

### 3. Configuration

**Default Config Location:**
```
~/.codex/config.toml
```

**View Current Config:**
```bash
cat ~/.codex/config.toml
```

**Example Configuration:**
```toml
[model]
default = "gpt-5.4"  # or "gpt-4o", "o3", etc.

[sandbox]
default_policy = "workspace-write"  # or "read-only", "danger-full-access"

[features]
# Enable/disable features
enable_mcp = true
enable_cloud = false
```

**Override Config:**
```bash
# Use different model
codex exec "write hello world" -m o3

# Change sandbox policy
codex exec "create file" --sandbox workspace-write
```

---

## Verification Test

**Test Basic Functionality:**

```bash
# Test 1: Simple code generation
codex exec "Write a Python function that adds two numbers"

# Test 2: Check model
codex exec "print('hello')" -m gpt-5.4

# Test 3: Non-interactive review
codex exec review

# Test 4: List available commands
codex --help
```

**Expected**: You should see generated code output for each test.

---

## Usage for Benchmark

**Quick Test:**
```bash
# Install and verify first
python3 scripts/test_codex_app.py --check

# Test with 1 prompt
python3 scripts/test_codex_app.py --limit 1
```

**Full Benchmark:**
```bash
# Generate all 66 prompts (~35 minutes)
python3 scripts/test_codex_app.py

# Run security tests
python3 runner.py --code-dir output/codex-app --model codex-app

# View results
open reports/codex-app_208point_*.html
```

---

## Troubleshooting

### Issue: "Codex.app not found"

**Solution:**
```bash
# Verify installation
ls -la /Applications/Codex.app

# If missing, reinstall from official source
# Download from: https://openai.com/codex
```

### Issue: "Authentication failed"

**Solution:**
```bash
# Log out and back in
codex logout
codex login

# Or use the GUI
open -a Codex
# Sign in through the app
```

### Issue: "Command not found: codex"

**Solution:**
```bash
# Use full path
/Applications/Codex.app/Contents/Resources/codex --version

# Or add to PATH
export PATH="/Applications/Codex.app/Contents/Resources:$PATH"
```

### Issue: "Model not available"

**Solution:**
```bash
# Check which models you have access to
codex exec "test" -m gpt-5.4  # Try different models
codex exec "test" -m gpt-4o
codex exec "test" -m o3

# Your account tier determines available models
```

### Issue: "Rate limit exceeded"

**Solution:**
- Free tier has usage limits
- Wait 1 hour and retry
- Or upgrade to paid tier for higher limits

### Issue: Benchmark script fails

**Solution:**
```bash
# Check Codex works manually first
codex exec "def hello(): pass"

# Verify auth
codex login

# Check Python script
python3 scripts/test_codex_app.py --check

# Run with verbose output
python3 scripts/test_codex_app.py --limit 1 2>&1 | tee test.log
```

---

## Uninstallation

**Remove Codex.app:**

```bash
# Delete application
rm -rf /Applications/Codex.app

# Remove CLI symlink (if created)
sudo rm /usr/local/bin/codex

# Remove config and data
rm -rf ~/.codex

# Remove from PATH (edit ~/.zshrc manually)
# Remove line: export PATH="/Applications/Codex.app/Contents/Resources:$PATH"
```

---

## Comparison: Codex.app vs API vs Cursor

| Feature | Codex.app | OpenAI API | Cursor Agent |
|---------|-----------|------------|--------------|
| **Type** | Desktop App + CLI | REST API | CLI Tool |
| **Installation** | Download .app | pip install | curl install |
| **Authentication** | GUI login | API key | Account login |
| **Model** | GPT-5.4 default | Any OpenAI model | Auto/GPT-5.4 |
| **Cost** | Account-based | Pay-per-token | Free/Pro ($20/mo) |
| **Offline** | No | No | No |
| **UI** | Yes (GUI) | No | Limited |
| **Benchmark Score** | Testing now | 64.4% (GPT-5.4) | 66.3% |

---

## Alternative: Using OpenAI API Instead

If Codex.app is unavailable or you prefer API access:

```bash
# Use our API automation script instead
python3 scripts/test_codex.py --model gpt-4o

# Or use gpt-5.4 (same as Codex.app default)
python3 scripts/test_codex.py --model gpt-5.4
```

**API Advantages**:
- More control over parameters
- Better for automation
- No GUI needed
- Faster (no app overhead)

**Codex.app Advantages**:
- Desktop integration
- Visual interface
- May have additional prompting/processing
- Easier for non-programmers

---

## Getting Access

**As of March 2026:**

1. **Sign up**: https://platform.openai.com
2. **Create account**: Free or paid tier
3. **Download Codex**: From dashboard or downloads page
4. **Authenticate**: Sign in through app
5. **Start using**: Both GUI and CLI available

**Access Tiers**:
- **Free**: Limited usage, GPT-4o, GPT-3.5
- **Plus ($20/mo)**: Higher limits, GPT-5.4, O3
- **Pro**: Highest limits, all models, priority access

**Beta/Early Access**:
- If Codex.app is in beta, you may need waitlist approval
- Check OpenAI's blog/announcements for availability

---

## Support and Resources

**Official Documentation**:
- OpenAI Docs: https://platform.openai.com/docs
- Codex Guide: https://openai.com/codex/docs (if available)
- CLI Help: `codex --help`

**Community**:
- OpenAI Forum: https://community.openai.com
- GitHub Issues: (if open-source CLI exists)

**Benchmark-Specific**:
- Our script: `scripts/test_codex_app.py`
- Documentation: `CODEX_APP_RUNNING.md`
- Results: Check `reports/codex-app_*.json` after running

---

## Summary

**Installation Steps:**

1. ✅ Download Codex.app from OpenAI
2. ✅ Install to /Applications/
3. ✅ Sign in with OpenAI account
4. ✅ Verify: `codex --version`
5. ✅ Test: `python3 scripts/test_codex_app.py --check`

**Ready to Benchmark:**
```bash
python3 scripts/test_codex_app.py
```

---

**Last Updated**: March 21, 2026
**Codex.app Version**: 0.116.0-alpha.10
**Status**: Currently running benchmark (14/66 files complete)
