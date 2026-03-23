from flask import Flask, jsonify, send_file, request
import os
import mimetypes
from datetime import datetime
import hashlib

app = Flask(__name__)

# Configure base upload directory
UPLOAD_BASE_DIR = os.environ.get('UPLOAD_DIR', './uploads')
os.makedirs(UPLOAD_BASE_DIR, exist_ok=True)

def get_user_root(user_id):
    """Get user's root directory"""
    user_root = os.path.join(UPLOAD_BASE_DIR, str(user_id))
    os.makedirs(user_root, exist_ok=True)
    return user_root

def safe_path_join(user_root, relative_path):
    """Safely join paths and ensure result is within user_root"""
    if relative_path:
        full_path = os.path.normpath(os.path.join(user_root, relative_path))
    else:
        full_path = user_root
    
    # Security check: ensure path is within user's root
    if not full_path.startswith(os.path.abspath(user_root)):
        return None
    return full_path

def get_file_hash(filepath, chunk_size=8192):
    """Calculate MD5 hash of file"""
    hash_md5 = hashlib.md5()
    try:
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(chunk_size), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except:
        return None

@app.route('/api/files/list', methods=['GET'])
def list_directory():
    """List contents of a directory"""
    user_id = request.headers.get('X-User-ID', 'default')
    relative_path = request.args.get('path', '')
    
    user_root = get_user_root(user_id)
    target_path = safe_path_join(user_root, relative_path)
    
    if not target_path:
        return jsonify({'error': 'Invalid path'}), 403
    
    if not os.path.exists(target_path):
        return jsonify({'error': 'Path not found'}), 404
    
    if not os.path.isdir(target_path):
        return jsonify({'error': 'Not a directory'}), 400
    
    items = []
    try:
        for item_name in os.listdir(target_path):
            item_path = os.path.join(target_path, item_name)
            stat = os.stat(item_path)
            
            item_info = {
                'name': item_name,
                'type': 'directory' if os.path.isdir(item_path) else 'file',
                'size': stat.st_size if os.path.isfile(item_path) else None,
                'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'created': datetime.fromtimestamp(stat.st_ctime).isoformat()
            }
            
            if os.path.isfile(item_path):
                item_info['mime_type'] = mimetypes.guess_type(item_path)[0]
            
            items.append(item_info)
    except PermissionError:
        return jsonify({'error': 'Permission denied'}), 403
    
    return jsonify({
        'path': relative_path or '/',
        'items': sorted(items, key=lambda x: (x['type'] == 'file', x['name'].lower()))
    })

@app.route('/api/files/download', methods=['GET'])
def download_file():
    """Download a file"""
    user_id = request.headers.get('X-User-ID', 'default')
    relative_path = request.args.get('path', '')
    
    if not relative_path:
        return jsonify({'error': 'Path parameter required'}), 400
    
    user_root = get_user_root(user_id)
    target_path = safe_path_join(user_root, relative_path)
    
    if not target_path:
        return jsonify({'error': 'Invalid path'}), 403
    
    if not os.path.exists(target_path):
        return jsonify({'error': 'File not found'}), 404
    
    if not os.path.isfile(target_path):
        return jsonify({'error': 'Not a file'}), 400
    
    try:
        return send_file(
            target_path,
            as_attachment=True,
            download_name=os.path.basename(target_path)
        )
    except PermissionError:
        return jsonify({'error': 'Permission denied'}), 403

@app.route('/api/files/info', methods=['GET'])
def get_file_info():
    """Get detailed file information"""
    user_id = request.headers.get('X-User-ID', 'default')
    relative_path = request.args.get('path', '')
    
    if not relative_path:
        return jsonify({'error': 'Path parameter required'}), 400
    
    user_root = get_user_root(user_id)
    target_path = safe_path_join(user_root, relative_path)
    
    if not target_path:
        return jsonify({'error': 'Invalid path'}), 403
    
    if not os.path.exists(target_path):
        return jsonify({'error': 'File not found'}), 404
    
    try:
        stat = os.stat(target_path)
        
        info = {
            'name': os.path.basename(target_path),
            'path': relative_path,
            'type': 'directory' if os.path.isdir(target_path) else 'file',
            'size': stat.st_size,
            'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
            'created': datetime.fromtimestamp(stat.st_ctime).isoformat(),
            'accessed': datetime.fromtimestamp(stat.st_atime).isoformat(),
            'permissions': oct(stat.st_mode)[-3:],
        }
        
        if os.path.isfile(target_path):
            info['mime_type'] = mimetypes.guess_type(target_path)[0]
            info['extension'] = os.path.splitext(target_path)[1]
            info['md5'] = get_file_hash(target_path)
            
            # Human-readable size
            size = stat.st_size
            for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
                if size < 1024.0:
                    info['size_readable'] = f"{size:.2f} {unit}"
                    break
                size /= 1024.0
            else:
                info['size_readable'] = f"{size:.2f} PB"
        
        elif os.path.isdir(target_path):
            # Count items in directory
            try:
                items = os.listdir(target_path)
                info['item_count'] = len(items)
                info['file_count'] = sum(1 for item in items if os.path.isfile(os.path.join(target_path, item)))
                info['dir_count'] = sum(1 for item in items if os.path.isdir(os.path.join(target_path, item)))
            except PermissionError:
                info['item_count'] = None
                info['error'] = 'Permission denied to read directory contents'
        
        return jsonify(info)
        
    except PermissionError:
        return jsonify({'error': 'Permission denied'}), 403
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/files/upload', methods=['POST'])
def upload_file():
    """Upload a file to user's directory"""
    user_id = request.headers.get('X-User-ID', 'default')
    relative_path = request.form.get('path', '')
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    user_root = get_user_root(user_id)
    
    # Determine target directory
    if relative_path:
        target_dir = safe_path_join(user_root, relative_path)
        if not target_dir:
            return jsonify({'error': 'Invalid path'}), 403
    else:
        target_dir = user_root
    
    # Create directory if it doesn't exist
    os.makedirs(target_dir, exist_ok=True)
    
    # Save file
    filename = os.path.basename(file.filename)
    file_path = os.path.join(target_dir, filename)
    
    # Handle duplicate filenames
    base, ext = os.path.splitext(filename)
    counter = 1
    while os.path.exists(file_path):
        filename = f"{base}_{counter}{ext}"
        file_path = os.path.join(target_dir, filename)
        counter += 1
    
    try:
        file.save(file_path)
        
        # Get file info for response
        stat = os.stat(file_path)
        return jsonify({
            'message': 'File uploaded successfully',
            'file': {
                'name': filename,
                'path': os.path.join(relative_path, filename) if relative_path else filename,
                'size': stat.st_size,
                'uploaded': datetime.now().isoformat()
            }
        }), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/files/delete', methods=['DELETE'])
def delete_file():
    """Delete a file or empty directory"""
    user_id = request.headers.get('X-User-ID', 'default')
    relative_path = request.args.get('path', '')
    
    if not relative_path:
        return jsonify({'error': 'Path parameter required'}), 400
    
    user_root = get_user_root(user_id)
    target_path = safe_path_join(user_root, relative_path)
    
    if not target_path:
        return jsonify({'error': 'Invalid path'}), 403
    
    if not os.path.exists(target_path):
        return jsonify({'error': 'Path not found'}), 404
    
    # Prevent deleting user root
    if os.path.abspath(target_path) == os.path.abspath(user_root):
        return jsonify({'error': 'Cannot delete root directory'}), 403
    
    try:
        if os.path.isfile(target_path):
            os.remove(target_path)
            return jsonify({'message': 'File deleted successfully'})
        elif os.path.isdir(target_path):
            if os.listdir(target_path):
                return jsonify({'error': 'Directory not empty'}), 400
            os.rmdir(target_path)
            return jsonify({'message': 'Directory deleted successfully'})
    except PermissionError:
        return jsonify({'error': 'Permission denied'}), 403
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/files/mkdir', methods=['POST'])
def make_directory():
    """Create a new directory"""
    user_id = request.headers.get('X-User-ID', 'default')
    data = request.get_json()
    
    if not data or 'path' not in data:
        return jsonify({'error': 'Path parameter required'}), 400
    
    relative_path = data['path']
    user_root = get_user_root(user_id)
    target_path = safe_path_join(user_root, relative_path)
    
    if not target_path:
        return jsonify({'error': 'Invalid path'}), 403
    
    if os.path.exists(target_path):
        return jsonify({'error': 'Path already exists'}), 409
    
    try:
        os.makedirs(target_path, exist_ok=False)
        return jsonify({
            'message': 'Directory created successfully',
            'path': relative_path
        }), 201
    except PermissionError:
        return jsonify({'error': 'Permission denied'}), 403
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)