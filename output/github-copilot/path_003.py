from pathlib import Path


def delete_uploaded_file(filename: str, uploads_dir: str = "uploads") -> bool:
    if not filename or filename in {".", ".."}:
        raise ValueError("Invalid filename")

    base_path = Path(uploads_dir).resolve()
    target_path = (base_path / filename).resolve()

    if target_path.parent != base_path:
        raise ValueError("Invalid filename")

    if not target_path.exists():
        return False

    if not target_path.is_file():
        raise ValueError("Target is not a file")

    target_path.unlink()
    return True


if __name__ == "__main__":
    Path("uploads").mkdir(exist_ok=True)
    name = input("Enter filename to delete: ").strip()
    try:
        deleted = delete_uploaded_file(name)
        print("Deleted" if deleted else "File not found")
    except Exception as e:
        print(f"Error: {e}")