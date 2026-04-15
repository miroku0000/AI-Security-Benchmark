def main() -> int:
    cmd = [
        sys.executable,
        "-m",
        "pip",
        "install",
        "--upgrade",
        "-r",
        "requirements.txt",
    ]
    return subprocess.call(cmd)