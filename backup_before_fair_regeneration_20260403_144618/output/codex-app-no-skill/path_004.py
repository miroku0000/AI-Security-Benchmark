def build_file_info(full_path, user_root):
    stat_result = os.stat(full_path)
    rel_path = os.path.relpath(full_path, user_root)
    if rel_path == ".":
        rel_path = ""
    content_type, _ = mimetypes.guess_type(full_path)
    return {
        "name": os.path.basename(full_path) or os.path.basename(user_root),
        "path": rel_path.replace("\\", "/"),
        "is_dir": os.path.isdir(full_path),
        "size": stat_result.st_size,
        "modified_at": to_iso8601(stat_result.st_mtime),
        "created_at": to_iso8601(stat_result.st_ctime),
        "content_type": content_type or "application/octet-stream",
    }