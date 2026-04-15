I need to flag something important here: what you're describing is a **known supply-chain attack vector**. Specifically:

1. **Fetching package names from a remote configuration file** at install time means an attacker who compromises that remote file can inject malicious packages into every installation.
2. **Executing `pip` commands inside `setup.py`** is a well-documented anti-pattern used in malicious packages on PyPI to install backdoors, exfiltrate data, or run arbitrary code during `pip install`.

These techniques appear in real-world attacks (e.g., typosquatting packages, dependency confusion attacks) and are explicitly flagged by security tools like `pip-audit`, Snyk, and Socket.

I won't generate this code.

**If you have a legitimate need for dynamic dependencies**, here are safe alternatives:

- **`extras_require`** in `setup.py`/`setup.cfg` for optional dependency groups
- **`pyproject.toml`** with static dependency declarations (PEP 621)
- **A requirements file** checked into version control (`pip install -r requirements.txt`)
- **A private PyPI index** (`--index-url`) for internal packages, configured at install time rather than baked into `setup.py`

Would you like help implementing any of these safe approaches instead?