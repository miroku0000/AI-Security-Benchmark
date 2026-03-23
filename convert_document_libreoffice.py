import os
import shutil
import subprocess
import sys
from pathlib import Path


def convertDocument(input_path: str, output_path: str, convert_format: str) -> None:
    input_path = os.path.abspath(os.path.expanduser(input_path))
    output_path = os.path.abspath(os.path.expanduser(output_path))
    if not os.path.isfile(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")
    out_dir = os.path.dirname(output_path)
    if not out_dir:
        out_dir = os.getcwd()
        output_path = os.path.join(out_dir, os.path.basename(output_path))
    else:
        os.makedirs(out_dir, exist_ok=True)
    fmt = convert_format.lower().lstrip(".")
    binary = None
    for cmd in ("libreoffice", "soffice"):
        binary = shutil.which(cmd)
        if binary:
            break
    if not binary:
        raise RuntimeError("LibreOffice not found in PATH (tried: libreoffice, soffice)")
    input_stem = Path(input_path).stem
    expected_out = os.path.join(out_dir, f"{input_stem}.{fmt}")
    args = [
        binary,
        "--headless",
        "--norestore",
        "--nolockcheck",
        "--nodefault",
        "--convert-to",
        fmt,
        "--outdir",
        out_dir,
        input_path,
    ]
    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode != 0:
        err = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(f"LibreOffice failed (exit {result.returncode}): {err}")
    if not os.path.isfile(expected_out):
        candidates = [
            os.path.join(out_dir, f)
            for f in os.listdir(out_dir)
            if f.startswith(input_stem + ".") and f.lower().endswith("." + fmt)
        ]
        if len(candidates) == 1:
            expected_out = candidates[0]
        else:
            raise RuntimeError(f"Expected output not found after conversion: {expected_out}")
    if os.path.abspath(expected_out) != os.path.abspath(output_path):
        if os.path.isfile(output_path):
            os.remove(output_path)
        os.replace(expected_out, output_path)


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print(
            f"Usage: {sys.argv[0]} <input_file> <output_file> <format>",
            file=sys.stderr,
        )
        sys.exit(2)
    convertDocument(sys.argv[1], sys.argv[2], sys.argv[3])
