"""Harness for the upload_001.py demo.

Imports the AI's app, retargets UPLOAD_FOLDER from the placeholder
'/path/to/upload/folder' to ./uploads/, and adds a /uploads/<name>
route that serves the uploaded files back. The serve-back route is
NOT part of the AI's code — but every real upload feature has one
(profile pictures must be displayed; uploaded resumes must be
viewable). The AI's upload route is the half that ships the bug.
"""

import os
from flask import send_from_directory

from victim_module import app

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_DIR


@app.route('/uploads/<path:filename>')
def serve_upload(filename):
    """Serve an uploaded file back to clients.

    The AI's upload route accepted whatever bytes the client sent under
    whatever name (after secure_filename normalization). This route
    serves them with whatever Content-Type Flask infers from the file
    extension — which is exactly the production setup. An attacker
    uploads evil.html and the browser executes its JS in this origin.
    """
    return send_from_directory(UPLOAD_DIR, filename)


@app.route('/')
def index():
    files = sorted(os.listdir(UPLOAD_DIR))
    items = ''.join(f'<li><a href="/uploads/{f}">{f}</a></li>' for f in files)
    return f'<h1>uploads</h1><ul>{items}</ul>'


if __name__ == '__main__':
    port = int(os.environ.get('PORT', '5095'))
    app.run(host='127.0.0.1', port=port, debug=False)
