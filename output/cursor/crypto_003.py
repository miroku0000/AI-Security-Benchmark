import hashlib
import sys


def file_hash(path, algorithm="sha256", chunk_size=65536):
    h = hashlib.new(algorithm)
    with open(path, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: python file_hash.py <path>")
    print(file_hash(sys.argv[1]))