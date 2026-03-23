import tarfile
import os

def extract_tar(tar_path, dest_dir):
    """
    Extracts a tar file to a destination directory.
    
    Args:
        tar_path: Path to the tar file
        dest_dir: Destination directory for extraction
    """
    # Create destination directory if it doesn't exist
    os.makedirs(dest_dir, exist_ok=True)
    
    # Open and extract the tar file
    with tarfile.open(tar_path, 'r:*') as tar:
        tar.extractall(path=dest_dir)