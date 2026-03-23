def delete_uploaded_file(filename: str, uploads_dir: str = "uploads") -> bool:
    if not filename or filename != Path(filename).name:
        raise ValueError("Invalid filename")