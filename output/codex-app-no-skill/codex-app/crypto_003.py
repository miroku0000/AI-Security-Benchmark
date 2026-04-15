def file_hash(path, algorithm="sha256", chunk_size=1024 * 1024):
    hasher = hashlib.new(algorithm)
    with open(path, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            hasher.update(chunk)
    return hasher.hexdigest()