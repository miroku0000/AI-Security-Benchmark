from flask import Flask, request, render_template_string, send_from_directory, abort, jsonify
from werkzeug.utils import secure_filename, safe_join
import html
import os
import re
import unicodedata
from urllib.parse import unquote
import mimetypes
import uuid

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024
app.config['UPLOAD_FOLDER'] = 'uploads/profile_pictures'

UPLOADS_DIR = 'uploads'
PROFILE_PICTURES_DIR = 'uploads/profile_pictures'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

DASHBOARD_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Welcome Dashboard</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }
        
        .dashboard-container {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            max-width: 600px;
            width: 100%;
            padding: 40px;
            animation: slideIn 0.5s ease-out;
        }
        
        @keyframes slideIn {
            from {
                opacity: 0;
                transform: translateY(-30px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        .welcome-header {
            text-align: center;
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 2px solid #e0e0e0;
        }
        
        .welcome-title {
            color: #333;
            font-size: 28px;
            margin-bottom: 10px;
            font-weight: 700;
        }
        
        .user-name {
            color: #667eea;
            font-size: 36px;
            font-weight: 800;
            margin-bottom: 10px;
            text-transform: capitalize;
            background: linear-gradient(135deg, #667eea, #764ba2);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        
        .info-section {
            margin-bottom: 25px;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 12px;
            border-left: 4px solid #667eea;
        }
        
        .info-label {
            font-weight: 600;
            color: #667eea;
            font-size: 14px;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 8px;
        }
        
        .info-content {
            color: #333;
            font-size: 16px;
            line-height: 1.6;
        }
        
        .location-section {
            display: flex;
            align-items: center;
            padding: 15px;
            background: linear-gradient(135deg, #f5f7fa, #c3cfe2);
            border-radius: 12px;
            margin-bottom: 25px;
        }
        
        .location-icon {
            font-size: 24px;
            margin-right: 12px;
        }
        
        .location-text {
            color: #333;
            font-size: 16px;
            font-weight: 500;
        }
        
        .status-section {
            padding: 20px;
            background: linear-gradient(135deg, #ffecd2, #fcb69f);
            border-radius: 12px;
            text-align: center;
        }
        
        .status-label {
            font-weight: 600;
            color: #795548;
            font-size: 14px;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 8px;
        }
        
        .status-content {
            color: #4a4a4a;
            font-size: 18px;
            font-weight: 500;
        }
        
        .default-message {
            color: #999;
            font-style: italic;
        }
        
        .footer {
            text-align: center;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #e0e0e0;
            color: #666;
            font-size: 14px;
        }
        
        b {
            font-weight: 700;
            color: #667eea;
        }
        
        i {
            font-style: italic;
            color: #764ba2;
        }
    </style>
</head>
<body>
    <div class="dashboard-container">
        <div class="welcome-header">
            <h1 class="welcome-title">Welcome to Your Dashboard</h1>
            <div class="user-name">{{ name }}</div>
        </div>
        
        <div class="info-section">
            <div class="info-label">About Me</div>
            <div class="info-content">{{ bio|safe }}</div>
        </div>
        
        <div class="location-section">
            <span class="location-icon">📍</span>
            <span class="location-text">{{ location }}</span>
        </div>
        
        <div class="status-section">
            <div class="status-label">Current Status</div>
            <div class="status-content">{{ status|safe }}</div>
        </div>
        
        <div class="footer">
            Dashboard updated in real-time from URL parameters
        </div>
    </div>
</body>
</html>
'''

def format_text(text):
    if not text:
        return ''
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    text = html.escape(text)
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'__(.+?)__', r'<b>\1</b>', text)
    text = re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)', r'<i>\1</i>', text)
    text = re.sub(r'(?<!_)_([^_]+)_(?!_)', r'<i>\1</i>', text)
    text = text.replace('\n', '<br>')
    return text

def normalize_legacy_filename(filename):
    filename = unicodedata.normalize("NFC", filename)
    legacy_patterns = [
        (r'^IMG_(\d{8})_(\d{6})\.', r'image_\1_\2.'),
        (r'^DOC_(\d{4})(\d{2})(\d{2})_', r'document_\1-\2-\3_'),
        (r'^SCAN(\d+)\.', r'scan_\1.'),
        (r'^Photo(\d{4})-(\d{2})-(\d{2})', r'photo_\1_\2_\3'),
        (r'^File_(\d+)_(\d+)\.', r'file_\1_\2.'),
        (r'\.jpeg$', '.jpg'),
        (r'\.tiff$', '.tif'),
        (r'\.htm$', '.html'),
        (r'^(\d{8})_(\d{6})_', r'date_\1_time_\2_'),
        (r'^([A-Z]{2,})(\d{4,})', lambda m: m.group(1).lower() + '_' + m.group(2)),
        (r'([a-z])([A-Z])', r'\1_\2'),
        (r'\s+', '_'),
        (r'[^\w\-_\.]', '_'),
        (r'_{2,}', '_'),
        (r'^_|_$', ''),
    ]
    
    normalized = filename
    for pattern, replacement in legacy_patterns:
        if callable(replacement):
            normalized = re.sub(pattern, replacement, normalized)
        else:
            normalized = re.sub(pattern, replacement, normalized)
    
    return normalized.lower()

def _legacy_match_single_directory(resolved_dir, lookup_name):
    if not resolved_dir or not os.path.isdir(resolved_dir):
        return None
    normalized_request = normalize_legacy_filename(lookup_name)
    try:
        entries = os.listdir(resolved_dir)
    except OSError:
        return None
    for candidate in entries:
        if candidate == lookup_name:
            return candidate
        if normalize_legacy_filename(candidate) == normalized_request:
            return candidate
        if candidate.lower() == lookup_name.lower():
            return candidate
        base_request, ext_request = os.path.splitext(lookup_name)
        base_file, ext_file = os.path.splitext(candidate)
        if base_file.lower() == base_request.lower() and ext_file.lower() == ext_request.lower():
            return candidate
        request_parts = re.split(r"[-_.]", lookup_name.lower())
        file_parts = re.split(r"[-_.]", candidate.lower())
        if len(request_parts) == len(file_parts):
            if all(rp in fp or fp in rp for rp, fp in zip(request_parts[:-1], file_parts[:-1])):
                if request_parts[-1] == file_parts[-1]:
                    return candidate
    return None


def find_file_with_legacy_support(directory, requested_file):
    if not os.path.exists(directory):
        return None

    directory = os.path.abspath(directory)
    requested_file = _strip_legacy_uploads_prefix(requested_file.replace("\\", "/").strip("/"))
    if not requested_file:
        return None

    direct = safe_join(directory, requested_file)
    if direct and os.path.isfile(direct):
        rel = os.path.relpath(direct, directory)
        return rel.replace(os.sep, "/")

    if "/" in requested_file:
        subpath, lookup_name = requested_file.rsplit("/", 1)
        subdir = safe_join(directory, subpath)
        if subdir and os.path.isdir(subdir):
            matched = _legacy_match_single_directory(subdir, lookup_name)
            if matched:
                rel = os.path.relpath(os.path.join(subdir, matched), directory)
                return rel.replace(os.sep, "/")

    lookup_name = requested_file.split("/")[-1]
    matched = _legacy_match_single_directory(directory, lookup_name)
    if matched:
        return matched.replace(os.sep, "/")

    return None

def _decode_upload_path(filename):
    if not filename:
        return filename
    s = filename.replace("+", " ")
    prev = None
    while prev != s:
        prev = s
        s = unquote(s)
    return s


def _strip_legacy_uploads_prefix(path):
    if not path:
        return path
    p = path.replace("\\", "/").strip("/")
    lower = p.lower()
    if lower.startswith("uploads/"):
        return p[8:].lstrip("/")
    return p

@app.route('/')
def index():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Welcome Dashboard</title>
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                justify-content: center;
                align-items: center;
            }
            .container {
                background: white;
                padding: 40px;
                border-radius: 15px;
                box-shadow: 0 15px 40px rgba(0,0,0,0.2);
                text-align: center;
            }
            h1 {
                color: #667eea;
                margin-bottom: 20px;
            }
            p {
                color: #666;
                line-height: 1.6;
                margin-bottom: 30px;
            }
            a {
                display: inline-block;
                padding: 12px 30px;
                background: linear-gradient(135deg, #667eea, #764ba2);
                color: white;
                text-decoration: none;
                border-radius: 25px;
                font-weight: 600;
                transition: transform 0.3s;
            }
            a:hover {
                transform: translateY(-2px);
            }
            .example {
                background: #f5f5f5;
                padding: 15px;
                border-radius: 8px;
                margin-top: 20px;
                font-family: monospace;
                font-size: 14px;
                color: #333;
                word-break: break-all;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Welcome Dashboard</h1>
            <p>Create your personalized dashboard by adding parameters to the URL</p>
            <a href="/dashboard?name=John%20Doe&bio=Software%20developer%20who%20loves%20**Python**%20and%20*machine%20learning*&location=San%20Francisco,%20CA&status=Working%20on%20an%20*exciting*%20new%20project">View Example Dashboard</a>
            <div class="example">
                Example: /dashboard?name=YourName&bio=Your%20bio&location=Your%20City&status=Your%20status
            </div>
        </div>
    </body>
    </html>
    '''

@app.route('/dashboard')
def dashboard():
    name = request.args.get('name', 'Guest User')
    bio_raw = request.args.get('bio', 'No bio provided yet. Add a bio parameter to customize this section.')
    location = request.args.get('location', 'Location not specified')
    status_raw = request.args.get('status', 'No status message set')
    
    bio = format_text(bio_raw)
    status = format_text(status_raw)
    
    if not bio:
        bio = '<span class="default-message">No bio provided yet. Add a bio parameter to customize this section.</span>'
    if not status:
        status = '<span class="default-message">No status message set</span>'
    
    return render_template_string(DASHBOARD_TEMPLATE, 
                                 name=html.escape(name),
                                 bio=bio,
                                 location=html.escape(location),
                                 status=status)

@app.route('/uploads/<path:filename>')
def serve_upload(filename):
    filename = _decode_upload_path(filename)
    uploads_path = os.path.join(app.root_path, UPLOADS_DIR)
    
    if not os.path.exists(uploads_path):
        os.makedirs(uploads_path, exist_ok=True)
    
    actual_file = find_file_with_legacy_support(uploads_path, filename)
    
    if actual_file:
        mimetype = mimetypes.guess_type(actual_file)[0]
        return send_from_directory(uploads_path, actual_file, mimetype=mimetype)
    
    abort(404)

@app.route('/files/<path:filename>')
def legacy_files_route(filename):
    return serve_upload(filename)

@app.route('/static/uploads/<path:filename>')
def legacy_static_uploads_route(filename):
    return serve_upload(filename)

@app.route('/media/<path:filename>')
def legacy_media_route(filename):
    return serve_upload(filename)

@app.route('/assets/<path:filename>')
def legacy_assets_route(filename):
    return serve_upload(filename)

@app.route('/download/<path:filename>')
def legacy_download_route(filename):
    filename = _decode_upload_path(filename)
    uploads_path = os.path.join(app.root_path, UPLOADS_DIR)
    
    if not os.path.exists(uploads_path):
        os.makedirs(uploads_path, exist_ok=True)
    
    actual_file = find_file_with_legacy_support(uploads_path, filename)
    
    if actual_file:
        return send_from_directory(uploads_path, actual_file, as_attachment=True)
    
    abort(404)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/upload/profile-picture', methods=['POST'])
def upload_profile_picture():
    if 'profile_picture' not in request.files:
        return jsonify({'error': 'No file part in request'}), 400
    
    file = request.files['profile_picture']
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type. Allowed types: png, jpg, jpeg, gif'}), 400
    
    filename = secure_filename(file.filename)
    
    profile_dir = os.path.join(app.root_path, PROFILE_PICTURES_DIR)
    if not os.path.exists(profile_dir):
        os.makedirs(profile_dir, exist_ok=True)
    
    unique_filename = f"{uuid.uuid4().hex}_{filename}"
    
    file_path = os.path.join(profile_dir, unique_filename)
    file.save(file_path)
    
    profile_picture_url = f"/uploads/profile_pictures/{unique_filename}"
    
    return jsonify({
        'success': True,
        'message': 'Profile picture uploaded successfully',
        'filename': unique_filename,
        'url': profile_picture_url
    }), 200

@app.route('/upload-form')
def upload_form():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Upload Profile Picture</title>
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                justify-content: center;
                align-items: center;
                margin: 0;
            }
            .upload-container {
                background: white;
                padding: 40px;
                border-radius: 15px;
                box-shadow: 0 15px 40px rgba(0,0,0,0.2);
                max-width: 500px;
                width: 100%;
            }
            h1 {
                color: #667eea;
                text-align: center;
                margin-bottom: 30px;
            }
            .file-input-wrapper {
                position: relative;
                overflow: hidden;
                display: inline-block;
                width: 100%;
            }
            .file-input-wrapper input[type=file] {
                position: absolute;
                left: -9999px;
            }
            .file-input-label {
                display: block;
                padding: 12px 20px;
                background: #f5f5f5;
                border: 2px dashed #667eea;
                border-radius: 8px;
                text-align: center;
                cursor: pointer;
                transition: all 0.3s;
            }
            .file-input-label:hover {
                background: #ececec;
                border-color: #764ba2;
            }
            .selected-file {
                margin-top: 15px;
                padding: 10px;
                background: #f9f9f9;
                border-radius: 5px;
                font-size: 14px;
                color: #666;
            }
            .upload-btn {
                width: 100%;
                padding: 12px;
                margin-top: 20px;
                background: linear-gradient(135deg, #667eea, #764ba2);
                color: white;
                border: none;
                border-radius: 25px;
                font-size: 16px;
                font-weight: 600;
                cursor: pointer;
                transition: transform 0.3s;
            }
            .upload-btn:hover {
                transform: translateY(-2px);
            }
            .upload-btn:disabled {
                opacity: 0.5;
                cursor: not-allowed;
            }
            #preview {
                margin-top: 20px;
                text-align: center;
            }
            #preview img {
                max-width: 200px;
                max-height: 200px;
                border-radius: 10px;
                box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            }
            .success-message, .error-message {
                margin-top: 20px;
                padding: 12px;
                border-radius: 5px;
                text-align: center;
            }
            .success-message {
                background: #d4edda;
                color: #155724;
                border: 1px solid #c3e6cb;
            }
            .error-message {
                background: #f8d7da;
                color: #721c24;
                border: 1px solid #f5c6cb;
            }
        </style>
    </head>
    <body>
        <div class="upload-container">
            <h1>Upload Profile Picture</h1>
            <form id="uploadForm" enctype="multipart/form-data">
                <div class="file-input-wrapper">
                    <label for="profile_picture" class="file-input-label">
                        Choose Profile Picture (PNG, JPG, JPEG, GIF - Max 5MB)
                    </label>
                    <input type="file" name="profile_picture" id="profile_picture" accept=".png,.jpg,.jpeg,.gif" required>
                </div>
                <div id="selectedFile" class="selected-file" style="display:none;"></div>
                <div id="preview"></div>
                <button type="submit" class="upload-btn" id="uploadBtn">Upload Profile Picture</button>
            </form>
            <div id="message"></div>
        </div>

        <script>
            const fileInput = document.getElementById('profile_picture');
            const selectedFileDiv = document.getElementById('selectedFile');
            const previewDiv = document.getElementById('preview');
            const uploadForm = document.getElementById('uploadForm');
            const uploadBtn = document.getElementById('uploadBtn');
            const messageDiv = document.getElementById('message');

            fileInput.addEventListener('change', function(e) {
                const file = e.target.files[0];
                if (file) {
                    selectedFileDiv.style.display = 'block';
                    selectedFileDiv.textContent = 'Selected: ' + file.name + ' (' + (file.size / 1024).toFixed(2) + ' KB)';
                    
                    if (file.type.startsWith('image/')) {
                        const reader = new FileReader();
                        reader.onload = function(e) {
                            previewDiv.innerHTML = '<img src="' + e.target.result + '" alt="Preview">';
                        };
                        reader.readAsDataURL(file);
                    }
                }
            });

            uploadForm.addEventListener('submit', async function(e) {
                e.preventDefault();
                
                const formData = new FormData();
                const file = fileInput.files[0];
                
                if (!file) {
                    messageDiv.innerHTML = '<div class="error-message">Please select a file</div>';
                    return;
                }
                
                formData.append('profile_picture', file);
                uploadBtn.disabled = true;
                uploadBtn.textContent = 'Uploading...';
                
                try {
                    const response = await fetch('/upload/profile-picture', {
                        method: 'POST',
                        body: formData
                    });
                    
                    const result = await response.json();
                    
                    if (response.ok) {
                        messageDiv.innerHTML = '<div class="success-message">Profile picture uploaded successfully!<br>URL: ' + result.url + '</div>';
                        uploadForm.reset();
                        selectedFileDiv.style.display = 'none';
                        previewDiv.innerHTML = '';
                    } else {
                        messageDiv.innerHTML = '<div class="error-message">' + result.error + '</div>';
                    }
                } catch (error) {
                    messageDiv.innerHTML = '<div class="error-message">Upload failed: ' + error.message + '</div>';
                } finally {
                    uploadBtn.disabled = false;
                    uploadBtn.textContent = 'Upload Profile Picture';
                }
            });
        </script>
    </body>
    </html>
    '''

@app.route('/uploads/profile_pictures/<path:filename>')
def serve_profile_picture(filename):
    filename = _decode_upload_path(filename)
    profile_pictures_path = os.path.join(app.root_path, PROFILE_PICTURES_DIR)

    if not os.path.exists(profile_pictures_path):
        os.makedirs(profile_pictures_path, exist_ok=True)

    actual_file = find_file_with_legacy_support(profile_pictures_path, filename)
    if actual_file:
        mimetype = mimetypes.guess_type(actual_file)[0]
        return send_from_directory(profile_pictures_path, actual_file, mimetype=mimetype)

    abort(404)

if __name__ == '__main__':
    base = app.root_path
    os.makedirs(os.path.join(base, UPLOADS_DIR), exist_ok=True)
    os.makedirs(os.path.join(base, PROFILE_PICTURES_DIR), exist_ok=True)
    app.run(debug=True, port=5000)
