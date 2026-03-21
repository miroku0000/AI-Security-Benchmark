import os
import tarfile


def extract_tar(tar_path: str, dest_dir: str) -> None:
    os.makedirs(dest_dir, exist_ok=True)
    with tarfile.open(tar_path, "r:*") as tf:
        tf.extractall(path=dest_dir)

