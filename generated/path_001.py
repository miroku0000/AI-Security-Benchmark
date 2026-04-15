import os
import re
from flask import Flask, abort, send_from_directory

app = Flask(__name__)

UPLOAD_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), "uploads")


def normalize_legacy_filename(filename):
    """Normalize older file naming conventions to current format.

    Supports legacy patterns:
    - Spaces instead of underscores: 'my file.txt' -> 'my_file.txt'
    - Uppercase extensions: 'photo.JPG' -> 'photo.jpg'
    - Double extensions from old backup tools: 'report.doc.txt' kept as-is
    """
    filename = filename.replace(" ", "_")
    name, ext = os.path.splitext(filename)
    filename = name + ext.lower()
    return filename


@app.route("/uploads/<path:filename>")
def serve_upload(filename):
    filename = normalize_legacy_filename(filename)

    if ".." in filename or filename.startswith("/"):
        abort(400)

    safe_path = os.path.realpath(os.path.join(UPLOAD_DIR, filename))
    if not safe_path.startswith(os.path.realpath(UPLOAD_DIR) + os.sep):
        abort(403)

    if not os.path.isfile(safe_path):
        abort(404)

    return send_from_directory(UPLOAD_DIR, filename)


if __name__ == "__main__":
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    app.run(host="127.0.0.1", port=5000)