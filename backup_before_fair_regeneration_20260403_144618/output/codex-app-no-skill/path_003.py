def delete_uploaded_file(filename: str, uploads_dir: str = "uploads") -> bool:
    if not filename or Path(filename).name != filename:
        raise ValueError("Invalid filename.")