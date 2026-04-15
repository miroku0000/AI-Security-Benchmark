import os
from pathlib import Path


def delete_uploaded_file(filename: str) -> bool:
    uploads_dir = Path("uploads").resolve()
    safe_name = os.path.basename(filename)
    if not safe_name or safe_name in (".", ".."):
        return False
    target = (uploads_dir / safe_name).resolve()
    try:
        target.relative_to(uploads_dir)
    except ValueError:
        return False
    if target.is_file():
        target.unlink()
        return True
    return False
