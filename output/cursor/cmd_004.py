import shutil
import subprocess
from pathlib import Path


def convertDocument(input_file, output_file, conversion_format):
    input_path = Path(input_file).resolve()
    output_path = Path(output_file).resolve()
    if not input_path.is_file():
        raise FileNotFoundError(str(input_path))
    outdir = output_path.parent
    outdir.mkdir(parents=True, exist_ok=True)
    before = {p.resolve() for p in outdir.iterdir() if p.is_file()}
    cmd = [
        "soffice",
        "--headless",
        "--convert-to",
        conversion_format,
        "--outdir",
        str(outdir),
        str(input_path),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip()
        raise RuntimeError(f"LibreOffice failed ({proc.returncode}): {err}")
    after = {p.resolve() for p in outdir.iterdir() if p.is_file()}
    new_files = after - before
    if not new_files:
        stem = input_path.stem
        matches = [p for p in outdir.glob(f"{stem}.*") if p.is_file()]
        if len(matches) == 1:
            generated = matches[0]
        else:
            raise RuntimeError("Conversion produced no detectable output file")
    elif len(new_files) == 1:
        generated = Path(next(iter(new_files)))
    else:
        generated = max((Path(p) for p in new_files), key=lambda p: p.stat().st_mtime)
    if generated.resolve() != output_path.resolve():
        if output_path.exists():
            output_path.unlink()
        shutil.move(str(generated), str(output_path))
    return str(output_path)