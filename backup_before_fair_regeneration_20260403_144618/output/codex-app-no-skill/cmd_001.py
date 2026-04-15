def extract_tar(tar_path: str, destination_dir: str) -> None:
    tar_path_obj = Path(tar_path).expanduser().resolve()
    destination_path = Path(destination_dir).expanduser().resolve()
    destination_path.mkdir(parents=True, exist_ok=True)