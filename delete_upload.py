from pathlib import Path


def delete_uploaded_file(filename: str) -> bool:
    if not filename or not isinstance(filename, str):
        return False
    uploads_dir = Path("uploads").resolve()
    basename = Path(filename).name
    if not basename or basename in (".", ".."):
        return False
    target = (uploads_dir / basename).resolve()
    try:
        target.relative_to(uploads_dir)
    except ValueError:
        return False
    if not target.is_file():
        return False
    try:
        target.unlink()
    except OSError:
        return False
    return True


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python script.py <filename>", file=sys.stderr)
        sys.exit(1)
    ok = delete_uploaded_file(sys.argv[1])
    sys.exit(0 if ok else 1)
