import os
import shutil
import subprocess
import tempfile


def _libreoffice_executable():
    for name in ("libreoffice", "soffice"):
        path = shutil.which(name)
        if path:
            return path
    mac = "/Applications/LibreOffice.app/Contents/MacOS/soffice"
    if os.path.isfile(mac):
        return mac
    return "libreoffice"


def convertDocument(input_path, output_path, conversion_format):
    input_path = os.path.abspath(os.path.expanduser(input_path))
    output_path = os.path.abspath(os.path.expanduser(output_path))
    if not os.path.isfile(input_path):
        raise FileNotFoundError(input_path)

    fmt = conversion_format.split(":", 1)[0]
    if "." in fmt:
        out_ext = fmt.rsplit(".", 1)[-1]
    else:
        out_ext = fmt

    stem = os.path.splitext(os.path.basename(input_path))[0]
    expected = f"{stem}.{out_ext}"

    lo = _libreoffice_executable()
    with tempfile.TemporaryDirectory() as tmpdir:
        cmd = [
            lo,
            "--headless",
            "--convert-to",
            conversion_format,
            "--outdir",
            tmpdir,
            input_path,
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        produced = os.path.join(tmpdir, expected)
        if not os.path.isfile(produced):
            names = os.listdir(tmpdir)
            if len(names) == 1:
                produced = os.path.join(tmpdir, names[0])
            else:
                raise FileNotFoundError(
                    f"Expected {expected!r} in {tmpdir}, found {names!r}"
                )

        parent = os.path.dirname(output_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        shutil.move(produced, output_path)
