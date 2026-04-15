def extract_tar(tar_path: str, destination_dir: str) -> None:
    tar_path = Path(tar_path).expanduser().resolve()
    destination = Path(destination_dir).expanduser().resolve()