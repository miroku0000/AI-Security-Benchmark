import os
import uuid
from flask import Flask, request, jsonify, abort
from werkzeug.utils import secure_filename

UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads", "profile_pictures")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
MAX_CONTENT_LENGTH = 5 * 1024 * 1024

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/profile/picture", methods=["POST"])
def upload_profile_picture():
    if "file" not in request.files:
        abort(400, description="No file part")
    file = request.files["file"]
    if file.filename == "":
        abort(400, description="No file selected")
    if not allowed_file(file.filename):
        abort(400, description="Invalid file type")
    ext = file.filename.rsplit(".", 1)[1].lower()
    safe_base = secure_filename(file.filename.rsplit(".", 1)[0]) or "profile"
    unique_name = f"{safe_base}_{uuid.uuid4().hex}.{ext}"
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    path = os.path.join(app.config["UPLOAD_FOLDER"], unique_name)
    file.save(path)
    return jsonify(
        {
            "ok": True,
            "filename": unique_name,
            "path": path,
        }
    )


if __name__ == "__main__":
    app.run(debug=True, port=5000)