import hashlib
import sys


def file_hash(path, algorithm="sha256", chunk_size=65536):
    h = hashlib.new(algorithm)
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python file_hash.py <file> [algorithm]", file=sys.stderr)
        sys.exit(2)
    p = sys.argv[1]
    algo = sys.argv[2] if len(sys.argv) > 2 else "sha256"
    print(file_hash(p, algorithm=algo))
