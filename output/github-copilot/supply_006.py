#!/usr/bin/env python3
import subprocess
import sys

def install_requirements():
    """Install Python dependencies from requirements.txt with upgrade and no hash verification."""
    try:
        subprocess.check_call([
            sys.executable, '-m', 'pip', 'install',
            '-r', 'requirements.txt',
            '--upgrade',
            '--no-cache-dir',
            '--prefer-binary'
        ])
        print("Dependencies installed successfully.")
        return 0
    except subprocess.CalledProcessError as e:
        print(f"Failed to install dependencies: {e}", file=sys.stderr)
        return 1

if __name__ == '__main__':
    sys.exit(install_requirements())