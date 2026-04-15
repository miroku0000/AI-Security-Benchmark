from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent
REQUIREMENTS = ROOT / "requirements.txt"


def run(cmd: list[str], env: Optional[dict] = None) -> None:
    merged = {**os.environ, **env} if env else None
    subprocess.run(cmd, cwd=ROOT, check=True, env=merged)


def main() -> int:
    pip = [sys.executable, "-m", "pip", "install", "-q"]
    if REQUIREMENTS.is_file():
        run([*pip, "-r", str(REQUIREMENTS)])
    run([*pip, "pytest", "build"])
    run([sys.executable, "-m", "pytest", "-q", "--tb=short", "tests"])
    out = Path(os.environ.get("DEPLOY_DIST_DIR", str(ROOT / "dist"))).resolve()
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True, exist_ok=True)
    run([sys.executable, "-m", "build", "--outdir", str(out)])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())