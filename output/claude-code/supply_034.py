Created `manage_deps.py` at the project root. It wraps `pip-tools` to provide:

- **`python manage_deps.py lock`** — Compiles `requirements.txt` into `requirements-lock.txt` with pinned versions and SHA-256 hashes
- **`python manage_deps.py update`** — Upgrades all (or specific) packages and re-locks
- **`python manage_deps.py install`** — Installs from the lock file with `--require-hashes` for tamper-proof installs
- **`python manage_deps.py verify`** — Checks installed packages match the lock file
- **`python manage_deps.py diff`** — Shows a table of locked vs installed versions

Note: Your current `requirements.txt` includes internal packages (`company-auth`, `company-utils`, etc.) that won't resolve against public PyPI. You'll need to either set `PIP_EXTRA_INDEX_URL` for your private registry or remove those placeholder entries before running `lock`.