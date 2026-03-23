from flask import Flask, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge
import os
import hashlib
import time
from PIL import Image
import magic

app = Flask(__name__)

# Security configurations
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5MB max file size
app.config['UPLOAD_FOLDER'] = 'profile_pictures'
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')

# Allowed extensions and MIME types
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
ALLOWED_MIME_TYPES = {
    'image/png': 'png',
    'image/jpeg': 'jpg',
    'image/jpg': 'jpg',
    'image/gif': 'gif',
    'image/webp': 'webp'
}

# Create upload directory if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def verify_image(file_path):
    """Verify the file is actually an image and safe"""
    try:
        # Check MIME type using python-magic
        mime = magic.from_file(file_path, mime=True)
        if mime not in ALLOWED_MIME_TYPES:
            return False, "Invalid file type"
        
        # Verify with PIL that it's a valid image
        with Image.open(file_path) as img:
            # Check image dimensions
            width, height = img.size
            if width > 4000 or height > 4000:
                return False, "Image dimensions too large"
            if width * height > 16000000:  # 16 megapixels
                return False, "Image resolution too high"
            
            # Verify format matches extension
            img.verify()
            
        return True, "Valid image"
    except Exception as e:
        return False, f"Invalid image file: {str(e)}"

def generate_unique_filename(original_filename, user_id):
    """Generate a unique filename using hash"""
    timestamp = str(time.time()).encode('utf-8')
    user_bytes = str(user_id).encode('utf-8')
    original_bytes = original_filename.encode('utf-8')
    
    hash_input = timestamp + user_bytes + original_bytes
    file_hash = hashlib.sha256(hash_input).hexdigest()[:16]
    
    extension = original_filename.rsplit('.', 1)[1].lower()
    return f"profile_{user_id}_{file_hash}.{extension}"

@app.route('/upload-profile-picture', methods=['POST'])
def upload_profile_picture():
    """Handle profile picture upload with security checks"""
    
    # Check if user is authenticated (implement your auth logic)
    user_id = request.headers.get('X-User-ID')
    if not user_id:
        return jsonify({'error': 'Authentication required'}), 401
    
    # Validate user_id format (alphanumeric only)
    if not user_id.replace('-', '').replace('_', '').isalnum():
        return jsonify({'error': 'Invalid user ID format'}), 400
    
    # Check if file is in request
    if 'profile_picture' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['profile_picture']
    
    # Check if file was selected
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    # Validate filename
    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type. Allowed: PNG, JPG, JPEG, GIF, WEBP'}), 400
    
    # Secure the filename
    filename = secure_filename(file.filename)
    if not filename:
        return jsonify({'error': 'Invalid filename'}), 400
    
    # Generate unique filename
    unique_filename = generate_unique_filename(filename, user_id)
    
    # Create user directory
    user_upload_dir = os.path.join(app.config['UPLOAD_FOLDER'], str(user_id))
    os.makedirs(user_upload_dir, exist_ok=True)
    
    # Full file path
    file_path = os.path.join(user_upload_dir, unique_filename)
    
    try:
        # Save file temporarily
        file.save(file_path)
        
        # Verify the uploaded file
        is_valid, message = verify_image(file_path)
        
        if not is_valid:
            # Remove invalid file
            os.remove(file_path)
            return jsonify({'error': message}), 400
        
        # Process image (resize for profile)
        with Image.open(file_path) as img:
            # Convert to RGB if necessary
            if img.mode not in ('RGB', 'RGBA'):
                img = img.convert('RGB')
            
            # Resize to standard profile picture size
            img.thumbnail((500, 500), Image.Resampling.LANCZOS)
            
            # Save processed image
            processed_filename = f"processed_{unique_filename}"
            processed_path = os.path.join(user_upload_dir, processed_filename)
            
            if processed_filename.lower().endswith('.png'):
                img.save(processed_path, 'PNG', optimize=True)
            else:
                img.save(processed_path, 'JPEG', quality=85, optimize=True)
        
        # Remove original and keep processed
        os.remove(file_path)
        
        # Generate secure URL
        profile_url = f"/profile-pictures/{user_id}/{processed_filename}"
        
        return jsonify({
            'success': True,
            'message': 'Profile picture uploaded successfully',
            'profile_url': profile_url,
            'filename': processed_filename
        }), 200
        
    except RequestEntityTooLarge:
        return jsonify({'error': 'File too large. Maximum size is 5MB'}), 413
    except Exception as e:
        # Clean up on error
        if os.path.exists(file_path):
            os.remove(file_path)
        
        # Log error securely (don't expose internal details)
        app.logger.error(f"Upload error for user {user_id}: {str(e)}")
        
        return jsonify({'error': 'Failed to process image'}), 500

@app.route('/profile-pictures/<user_id>/<filename>', methods=['GET'])
def serve_profile_picture(user_id, filename):
    """Serve profile pictures with security checks"""
    
    # Validate user_id format
    if not user_id.replace('-', '').replace('_', '').isalnum():
        return jsonify({'error': 'Invalid user ID'}), 400
    
    # Validate filename
    if not secure_filename(filename) == filename:
        return jsonify({'error': 'Invalid filename'}), 400
    
    # Check file extension
    if not allowed_file(filename):
        return jsonify({'error': 'Invalid file type'}), 400
    
    user_upload_dir = os.path.join(app.config['UPLOAD_FOLDER'], user_id)
    
    # Prevent directory traversal
    safe_path = os.path.join(user_upload_dir, filename)
    if not safe_path.startswith(os.path.abspath(user_upload_dir)):
        return jsonify({'error': 'Invalid path'}), 400
    
    if not os.path.exists(safe_path):
        return jsonify({'error': 'File not found'}), 404
    
    return send_from_directory(user_upload_dir, filename, mimetype='image/jpeg')

@app.errorhandler(RequestEntityTooLarge)
def handle_file_too_large(e):
    """Handle file size limit exceeded"""
    return jsonify({'error': 'File too large. Maximum size is 5MB'}), 413

@app.errorhandler(500)
def handle_server_error(e):
    """Handle internal server errors"""
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    app.run(debug=False, host='127.0.0.1', port=5000)