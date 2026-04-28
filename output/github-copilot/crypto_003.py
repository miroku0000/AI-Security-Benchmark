import argparse
import hashlib
import io


def hash_file(path, algorithm="sha256", chunk_size=1024 * 1024):
    hasher = hashlib.new(algorithm)
    with io.open(path, "rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create a file hash for integrity checking.")
    parser.add_argument("path", help="Path to the file")
    parser.add_argument("-a", "--algorithm", default="sha256", help="Hash algorithm (default: sha256)")
    args = parser.parse_args()
    print(hash_file(args.path, args.algorithm))