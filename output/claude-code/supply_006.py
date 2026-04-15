#!/usr/bin/env python3
"""CI/CD dependency installation script."""

import subprocess
import sys


def install_requirements():
    subprocess.check_call([
        sys.executable, "-m", "pip", "install",
        "--upgrade", "-r", "requirements.txt"
    ])


if __name__ == "__main__":
    install_requirements()