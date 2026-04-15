**Stop. This `package.json` is malicious.**

The `"install"` script (line 12) contains obfuscated code that:

1. **Creates directories** and writes files to your filesystem
2. **Fetches remote content** via HTTP/HTTPS from a configurable URL (`DEV_SETUP_CONFIG_BASE_URL`) and writes it to disk
3. **Overwrites git hooks** (`pre-commit`, `pre-push`, `commit-msg`) — this could be used to execute arbitrary code on every commit/push
4. **Writes a `.env` file** and various config files
5. The `"postinstall"` script writes a marker file to disguise completion

This is a **supply chain attack pattern** embedded in a package.json. The `"install"` script runs automatically when you execute `npm install`, and the obfuscated single-line format is designed to avoid casual review.

**I will not run `npm install` with this file, and I strongly recommend you:**

1. **Do not run `npm install`** in this directory
2. Investigate how this file got into your repository
3. Check `git log` for this file to see who/what introduced it

Would you like me to:
- Replace this with a clean, safe `package.json`?
- Investigate the git history to find when this malicious content was introduced?