import argparse
import os
import shutil
import subprocess
import tempfile
from pathlib import Path


def _find_libreoffice_executable():
    candidates = [
        shutil.which("libreoffice"),
        shutil.which("soffice"),
        "/usr/bin/libreoffice",
        "/usr/bin/soffice",
        "/snap/bin/libreoffice",
        "/Applications/LibreOffice.app/Contents/MacOS/soffice",
        r"C:\Program Files\LibreOffice\program\soffice.exe",
        r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
    ]
    for candidate in candidates:
        if candidate and os.path.exists(candidate):
            return candidate
    raise FileNotFoundError("LibreOffice executable not found. Install LibreOffice or add it to PATH.")


def _normalize_format(conversion_format):
    normalized = conversion_format.strip().lower().lstrip(".")
    aliases = {
        "word": "docx",
        "msword": "docx",
        "jpeg": "jpg",
        "tiff": "tif",
    }
    return aliases.get(normalized, normalized)


def _user_installation_uri(directory):
    return Path(directory).resolve().as_uri()


def convertDocument(input_file, output_file, conversion_format):
    if not input_file or not output_file or not conversion_format:
        raise ValueError("input_file, output_file, and conversion_format are required.")

    input_path = Path(input_file).expanduser().resolve()
    output_path = Path(output_file).expanduser().resolve()
    target_format = _normalize_format(conversion_format)

    if not input_path.is_file():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    libreoffice = _find_libreoffice_executable()
    expected_output = output_path.parent / f"{input_path.stem}.{target_format}"

    with tempfile.TemporaryDirectory(prefix="libreoffice-profile-") as profile_dir:
        command = [
            libreoffice,
            "--headless",
            f"-env:UserInstallation={_user_installation_uri(profile_dir)}",
            "--convert-to",
            target_format,
            "--outdir",
            str(output_path.parent),
            str(input_path),
        ]

        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )

    if result.returncode != 0:
        raise RuntimeError(
            "LibreOffice conversion failed.\n"
            f"Command: {' '.join(command)}\n"
            f"STDOUT: {result.stdout}\n"
            f"STDERR: {result.stderr}"
        )

    if not expected_output.exists():
        matches = sorted(
            path for path in output_path.parent.glob(f"*.{target_format}")
            if path.stem.lower() == input_path.stem.lower()
        )
        if matches:
            expected_output = matches[0]
        else:
            raise FileNotFoundError(
                f"Converted file not found. Expected: {expected_output}\n"
                f"STDOUT: {result.stdout}\n"
                f"STDERR: {result.stderr}"
            )

    if expected_output != output_path:
        if output_path.exists():
            output_path.unlink()
        shutil.move(str(expected_output), str(output_path))

    return str(output_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert documents using LibreOffice headless mode.")
    parser.add_argument("input_file", help="Path to the input file")
    parser.add_argument("output_file", help="Path to the output file")
    parser.add_argument("conversion_format", help="Target format, e.g. pdf, docx, odt")
    args = parser.parse_args()

    print(convertDocument(args.input_file, args.output_file, args.conversion_format))