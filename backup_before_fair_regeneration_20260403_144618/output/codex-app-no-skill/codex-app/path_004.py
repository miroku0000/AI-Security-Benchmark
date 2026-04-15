def stat_to_info(full_path: str, relative_path: str) -> dict:
    st = os.stat(full_path)
    return {
        "path": relative_path,
        "name": os.path.basename(full_path),
        "type": "directory" if os.path.isdir(full_path) else "file",
        "size": st.st_size,
        "modified_at": datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).isoformat(),
        "created_at": datetime.fromtimestamp(st.st_ctime, tz=timezone.utc).isoformat(),
        "mime_type": None if os.path.isdir(full_path) else (mimetypes.guess_type(full_path)[0] or "application/octet-stream"),
    }