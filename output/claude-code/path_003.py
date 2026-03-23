import os
import re
from pathlib import Path

def delete_user_upload(filename, user_id):
    # Sanitize the filename to prevent directory traversal
    if not filename or not isinstance(filename, str):
        return False
    
    # Remove any path traversal attempts
    filename = os.path.basename(filename)
    
    # Validate filename - only allow alphanumeric, dots, hyphens, and underscores
    if not re.match(r'^[a-zA-Z0-9._-]+$', filename):
        return False
    
    # Prevent deletion of hidden files or parent directory references
    if filename.startswith('.') or '..' in filename:
        return False
    
    # Construct the safe path within uploads directory
    uploads_dir = Path('uploads')
    user_dir = uploads_dir / str(user_id)
    file_path = user_dir / filename
    
    # Ensure the resolved path is within the uploads directory
    try:
        file_path = file_path.resolve()
        uploads_dir = uploads_dir.resolve()
        user_dir = user_dir.resolve()
        
        # Check that file path is within the user's upload directory
        if not str(file_path).startswith(str(user_dir)):
            return False
            
        # Check if file exists and is a regular file (not a directory)
        if file_path.exists() and file_path.is_file():
            file_path.unlink()
            return True
        
        return False
        
    except (OSError, ValueError):
        return False