import argparse
import tarfile
from pathlib import Path


def extract_tar(archive_path, dest_dir):
    archive_path = Path(archive_path).resolve()
    dest_dir = Path(dest_dir).resolve()
    if not archive_path.is_file():
        raise FileNotFoundError(f"not a file: {archive_path}")
    dest_dir.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive_path, mode="r:*") as tf:
        try:
            tf.extractall(path=dest_dir, filter="data")
        except TypeError:
            tf.extractall(path=dest_dir)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("archive")
    parser.add_argument("dest_dir")
    args = parser.parse_args()
    extract_tar(args.archive, args.dest_dir)