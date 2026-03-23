from flask import Flask, request, jsonify, send_file, abort, send_from_directory
import os
import os.path
from datetime import datetime
import mimetypes
import hashlib
import re
from urllib.parse import unquote
import unicodedata
import string

app = Flask(__name__)

# Configuration
UPLOAD_ROOT = os.environ.get('UPLOAD_ROOT', '/tmp/user_uploads')
MAX_PATH_DEPTH = 10
UPLOADS_DIR = os.environ.get('UPLOADS_DIR', 'uploads')
ENABLE_LEGACY_SUPPORT = os.environ.get('ENABLE_LEGACY_SUPPORT', 'true').lower() == 'true'
LEGACY_NAMING_PATTERNS = [
    r'^\d{8}_\d{6}_',  # YYYYMMDD_HHMMSS_ prefix
    r'^[A-Z]{3}\d{4}_',  # XXX0000_ prefix
    r'_v\d+\.',  # _v1, _v2 versioning
    r'\.bak\d*$',  # .bak, .bak1, .bak2 extensions
    r'\s+',  # Spaces in filenames
    r'[^\x00-\x7F]+',  # Non-ASCII characters
]

def get_user_root(user_id):
    """Get the root directory for a specific user"""
    user_root = os.path.join(UPLOAD_ROOT, str(user_id))
    os.makedirs(user_root, exist_ok=True)
    return user_root

def get_uploads_directory(user_id):
    """Get the uploads directory for a specific user"""
    user_root = get_user_root(user_id)
    uploads_path = os.path.join(user_root, UPLOADS_DIR)
    os.makedirs(uploads_path, exist_ok=True)
    return uploads_path

def normalize_legacy_filename(filename):
    """Normalize legacy filename to handle older naming conventions"""
    if not ENABLE_LEGACY_SUPPORT:
        return filename
    
    # Remove non-ASCII characters
    normalized = unicodedata.normalize('NFKD', filename)
    normalized = normalized.encode('ascii', 'ignore').decode('ascii')
    
    # Handle spaces - replace with underscores
    normalized = normalized.replace(' ', '_')
    
    # Remove multiple consecutive underscores
    normalized = re.sub(r'_{2,}', '_', normalized)
    
    # Keep original extension
    name, ext = os.path.splitext(normalized)
    
    # Clean up the name part
    name = re.sub(r'[^\w\-_]', '', name)
    
    # Ensure we have a valid filename
    if not name:
        name = 'file'
    
    return name + ext

def find_legacy_file(directory, requested_name):
    """Find a file using legacy naming patterns"""
    if not ENABLE_LEGACY_SUPPORT or not os.path.isdir(directory):
        return None
    
    requested_lower = requested_name.lower()
    normalized_requested = normalize_legacy_filename(requested_name)
    
    for filename in os.listdir(directory):
        # Direct match
        if filename == requested_name:
            return filename
        
        # Case-insensitive match
        if filename.lower() == requested_lower:
            return filename
        
        # Normalized match
        if normalize_legacy_filename(filename) == normalized_requested:
            return filename
        
        # Check if base names match (ignoring versioning)
        base_requested = re.sub(r'_v\d+', '', requested_name)
        base_file = re.sub(r'_v\d+', '', filename)
        if base_file == base_requested:
            return filename
        
        # Check for backup extensions
        if filename.startswith(requested_name) and re.search(r'\.bak\d*$', filename):
            return filename
    
    return None

def validate_and_resolve_path(user_root, relative_path):
    """Validate and resolve a relative path within the user's root directory"""
    # Normalize the path to handle '..' and clean it up
    normalized_path = os.path.normpath(relative_path)
    
    # Remove leading separators
    if normalized_path.startswith(os.sep):
        normalized_path = normalized_path[1:]
    
    # Construct the full path
    full_path = os.path.join(user_root, normalized_path)
    
    # Resolve to absolute path and check if it's within user_root
    resolved_path = os.path.abspath(full_path)
    user_root_abs = os.path.abspath(user_root)
    
    # Security check: ensure the resolved path is within the user's root
    if not resolved_path.startswith(user_root_abs + os.sep) and resolved_path != user_root_abs:
        return None
    
    # Check path depth to prevent excessive nesting
    relative_parts = os.path.relpath(resolved_path, user_root_abs).split(os.sep)
    if len(relative_parts) > MAX_PATH_DEPTH:
        return None
    
    return resolved_path

def get_file_hash(file_path, algorithm='sha256'):
    """Calculate file hash"""
    hash_func = hashlib.new(algorithm)
    try:
        with open(file_path, 'rb') as f:
            while chunk := f.read(8192):
                hash_func.update(chunk)
        return hash_func.hexdigest()
    except:
        return None

@app.route('/api/files/list', methods=['GET'])
def list_directory():
    """List contents of a directory"""
    user_id = request.headers.get('X-User-ID')
    if not user_id:
        return jsonify({'error': 'User ID required in X-User-ID header'}), 401
    
    path = request.args.get('path', '')
    user_root = get_user_root(user_id)
    
    resolved_path = validate_and_resolve_path(user_root, path)
    if resolved_path is None:
        return jsonify({'error': 'Invalid path'}), 400
    
    if not os.path.exists(resolved_path):
        return jsonify({'error': 'Path does not exist'}), 404
    
    if not os.path.isdir(resolved_path):
        return jsonify({'error': 'Path is not a directory'}), 400
    
    try:
        items = []
        for item_name in os.listdir(resolved_path):
            item_path = os.path.join(resolved_path, item_name)
            stat = os.stat(item_path)
            
            item_info = {
                'name': item_name,
                'type': 'directory' if os.path.isdir(item_path) else 'file',
                'size': stat.st_size if not os.path.isdir(item_path) else 0,
                'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'created': datetime.fromtimestamp(stat.st_ctime).isoformat(),
            }
            
            if not os.path.isdir(item_path):
                item_info['mime_type'] = mimetypes.guess_type(item_name)[0] or 'application/octet-stream'
            
            items.append(item_info)
        
        # Sort: directories first, then files, alphabetically
        items.sort(key=lambda x: (x['type'] != 'directory', x['name'].lower()))
        
        current_path = os.path.relpath(resolved_path, user_root)
        if current_path == '.':
            current_path = ''
        
        return jsonify({
            'path': current_path,
            'items': items,
            'count': len(items)
        })
    
    except PermissionError:
        return jsonify({'error': 'Permission denied'}), 403
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/files/download', methods=['GET'])
def download_file():
    """Download a file"""
    user_id = request.headers.get('X-User-ID')
    if not user_id:
        return jsonify({'error': 'User ID required in X-User-ID header'}), 401
    
    path = request.args.get('path', '')
    if not path:
        return jsonify({'error': 'Path parameter required'}), 400
    
    user_root = get_user_root(user_id)
    resolved_path = validate_and_resolve_path(user_root, path)
    
    if resolved_path is None:
        return jsonify({'error': 'Invalid path'}), 400
    
    if not os.path.exists(resolved_path):
        return jsonify({'error': 'File does not exist'}), 404
    
    if os.path.isdir(resolved_path):
        return jsonify({'error': 'Cannot download directory'}), 400
    
    try:
        return send_file(
            resolved_path,
            as_attachment=True,
            download_name=os.path.basename(resolved_path),
            mimetype=mimetypes.guess_type(resolved_path)[0] or 'application/octet-stream'
        )
    except PermissionError:
        return jsonify({'error': 'Permission denied'}), 403
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/files/info', methods=['GET'])
def get_file_info():
    """Get detailed information about a file or directory"""
    user_id = request.headers.get('X-User-ID')
    if not user_id:
        return jsonify({'error': 'User ID required in X-User-ID header'}), 401
    
    path = request.args.get('path', '')
    user_root = get_user_root(user_id)
    
    resolved_path = validate_and_resolve_path(user_root, path)
    if resolved_path is None:
        return jsonify({'error': 'Invalid path'}), 400
    
    if not os.path.exists(resolved_path):
        return jsonify({'error': 'Path does not exist'}), 404
    
    try:
        stat = os.stat(resolved_path)
        is_dir = os.path.isdir(resolved_path)
        
        relative_path = os.path.relpath(resolved_path, user_root)
        if relative_path == '.':
            relative_path = ''
        
        info = {
            'name': os.path.basename(resolved_path) if relative_path else '/',
            'path': relative_path,
            'type': 'directory' if is_dir else 'file',
            'size': stat.st_size,
            'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
            'created': datetime.fromtimestamp(stat.st_ctime).isoformat(),
            'accessed': datetime.fromtimestamp(stat.st_atime).isoformat(),
            'permissions': oct(stat.st_mode)[-3:],
            'uid': stat.st_uid,
            'gid': stat.st_gid,
        }
        
        if not is_dir:
            info['mime_type'] = mimetypes.guess_type(resolved_path)[0] or 'application/octet-stream'
            
            # Add file hash for files under 100MB
            if stat.st_size < 100 * 1024 * 1024:
                file_hash = get_file_hash(resolved_path)
                if file_hash:
                    info['sha256'] = file_hash
        else:
            # For directories, count items
            try:
                info['item_count'] = len(os.listdir(resolved_path))
            except:
                info['item_count'] = 0
        
        # Get parent directory
        parent_path = os.path.dirname(relative_path)
        if parent_path and parent_path != relative_path:
            info['parent'] = parent_path
        elif relative_path:
            info['parent'] = ''
        
        return jsonify(info)
    
    except PermissionError:
        return jsonify({'error': 'Permission denied'}), 403
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/files/tree', methods=['GET'])
def get_directory_tree():
    """Get directory tree structure"""
    user_id = request.headers.get('X-User-ID')
    if not user_id:
        return jsonify({'error': 'User ID required in X-User-ID header'}), 401
    
    path = request.args.get('path', '')
    max_depth = min(int(request.args.get('depth', 2)), 5)
    
    user_root = get_user_root(user_id)
    resolved_path = validate_and_resolve_path(user_root, path)
    
    if resolved_path is None:
        return jsonify({'error': 'Invalid path'}), 400
    
    if not os.path.exists(resolved_path):
        return jsonify({'error': 'Path does not exist'}), 404
    
    if not os.path.isdir(resolved_path):
        return jsonify({'error': 'Path is not a directory'}), 400
    
    def build_tree(dir_path, current_depth=0):
        if current_depth >= max_depth:
            return None
        
        tree = []
        try:
            for item_name in sorted(os.listdir(dir_path)):
                item_path = os.path.join(dir_path, item_name)
                is_dir = os.path.isdir(item_path)
                
                node = {
                    'name': item_name,
                    'type': 'directory' if is_dir else 'file'
                }
                
                if is_dir:
                    children = build_tree(item_path, current_depth + 1)
                    if children is not None:
                        node['children'] = children
                
                tree.append(node)
        except PermissionError:
            pass
        
        return tree
    
    try:
        tree = build_tree(resolved_path)
        relative_path = os.path.relpath(resolved_path, user_root)
        if relative_path == '.':
            relative_path = ''
        
        return jsonify({
            'path': relative_path,
            'tree': tree
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/files/search', methods=['GET'])
def search_files():
    """Search for files by name pattern"""
    user_id = request.headers.get('X-User-ID')
    if not user_id:
        return jsonify({'error': 'User ID required in X-User-ID header'}), 401
    
    pattern = request.args.get('pattern', '')
    path = request.args.get('path', '')
    
    if not pattern:
        return jsonify({'error': 'Search pattern required'}), 400
    
    user_root = get_user_root(user_id)
    resolved_path = validate_and_resolve_path(user_root, path)
    
    if resolved_path is None:
        return jsonify({'error': 'Invalid path'}), 400
    
    if not os.path.exists(resolved_path):
        return jsonify({'error': 'Path does not exist'}), 404
    
    if not os.path.isdir(resolved_path):
        return jsonify({'error': 'Path is not a directory'}), 400
    
    results = []
    pattern_lower = pattern.lower()
    
    try:
        for root, dirs, files in os.walk(resolved_path):
            # Limit search depth
            depth = root[len(resolved_path):].count(os.sep)
            if depth > 5:
                dirs.clear()
                continue
            
            # Search in current directory
            for name in files + dirs:
                if pattern_lower in name.lower():
                    full_path = os.path.join(root, name)
                    relative_to_user = os.path.relpath(full_path, user_root)
                    
                    results.append({
                        'name': name,
                        'path': relative_to_user,
                        'type': 'directory' if name in dirs else 'file',
                        'size': os.path.getsize(full_path) if name in files else 0
                    })
            
            # Limit results
            if len(results) >= 100:
                break
        
        return jsonify({
            'pattern': pattern,
            'results': results[:100],
            'count': len(results[:100])
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/files/stats', methods=['GET'])
def get_storage_stats():
    """Get storage statistics for user"""
    user_id = request.headers.get('X-User-ID')
    if not user_id:
        return jsonify({'error': 'User ID required in X-User-ID header'}), 401
    
    user_root = get_user_root(user_id)
    
    total_size = 0
    file_count = 0
    dir_count = 0
    
    try:
        for root, dirs, files in os.walk(user_root):
            dir_count += len(dirs)
            file_count += len(files)
            for name in files:
                try:
                    total_size += os.path.getsize(os.path.join(root, name))
                except:
                    pass
        
        return jsonify({
            'total_size': total_size,
            'total_size_mb': round(total_size / (1024 * 1024), 2),
            'file_count': file_count,
            'directory_count': dir_count,
            'user_id': user_id
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)