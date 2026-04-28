import argparse
import os
import tarfile
from pathlib import Path


def extract_tar(tar_path: str, destination_dir: str) -> None:
    tar_file = Path(tar_path).expanduser().resolve()
    destination = Path(destination_dir).expanduser().resolve()

    if not tar_file.is_file():
        raise FileNotFoundError(f"Tar file not found: {tar_file}")

    destination.mkdir(parents=True, exist_ok=True)

    with tarfile.open(tar_file, "r:*") as tar:
        for member in tar.getmembers():
            if member.issym() or member.islnk():
                raise ValueError(f"Refusing to extract link: {member.name}")
            if member.isdev():
                raise ValueError(f"Refusing to extract device file: {member.name}")

            target_path = (destination / member.name).resolve()
            if os.path.commonpath([str(destination), str(target_path)]) != str(destination):
                raise ValueError(f"Blocked path traversal attempt: {member.name}")

        tar.extractall(path=destination)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Safely extract a tar archive.")
    parser.add_argument("tar_path", help="Path to the tar archive")
    parser.add_argument("destination_dir", help="Directory to extract into")
    args = parser.parse_args()

    extract_tar(args.tar_path, args.destination_dir)