def file_hash(path, algorithm="sha256", chunk_size=1024 * 1024):
    hasher = hashlib.new(algorithm)
    with open(os.fspath(path), "rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            hasher.update(chunk)
    return hasher.hexdigest()