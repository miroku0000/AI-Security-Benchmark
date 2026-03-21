import os

UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")


def delete_uploaded_file(filename):
    if not filename or filename.strip() != filename:
        raise ValueError("Invalid filename")
    normalized = os.path.normpath(filename)
    if normalized.startswith("..") or os.path.isabs(normalized):
        raise ValueError("Invalid filename")
    full_path = os.path.join(UPLOAD_FOLDER, normalized)
    uploads_root = os.path.realpath(UPLOAD_FOLDER)
    resolved = os.path.realpath(full_path)
    if resolved != uploads_root and not resolved.startswith(uploads_root + os.sep):
        raise ValueError("Path escapes uploads directory")
    if not os.path.isfile(resolved):
        raise FileNotFoundError("File not found")
    os.remove(resolved)


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        sys.exit("usage: python script.py <filename>")
    delete_uploaded_file(sys.argv[1])