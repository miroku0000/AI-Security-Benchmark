import hashlib
from pathlib import Path


def file_hash(path, algorithm="sha256", chunk_size=65536):
    """Return hex digest of file contents using hashlib (chunked for large files)."""
    path = Path(path)
    h = hashlib.new(algorithm)
    with path.open("rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        sys.exit("usage: python <script> <file> [algorithm]")
    p = sys.argv[1]
    algo = sys.argv[2] if len(sys.argv) > 2 else "sha256"
    print(file_hash(p, algorithm=algo))