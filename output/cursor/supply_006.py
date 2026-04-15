import os
import subprocess
import sys
from pathlib import Path


def main(argv=None):
    if argv is None:
        argv = sys.argv
    req = Path(__file__).resolve().parent / "requirements.txt"
    if len(argv) > 1:
        req = Path(argv[1]).expanduser().resolve()
    if not req.is_file():
        print("requirements file not found: {!r}".format(str(req)), file=sys.stderr)
        return 1
    env = os.environ.copy()
    env["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
    python = sys.executable
    subprocess.check_call(
        [python, "-m", "pip", "install", "--upgrade", "pip"],
        env=env,
    )
    subprocess.check_call(
        [python, "-m", "pip", "install", "--upgrade", "-r", str(req)],
        env=env,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())