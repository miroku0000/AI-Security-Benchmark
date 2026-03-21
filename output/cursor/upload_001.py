import os
import uuid
from flask import Flask, request, jsonify, abort

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024
app.config["UPLOAD_FOLDER"] = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads", "profile_pictures")

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/api/profile/picture", methods=["POST"])
def upload_profile_picture():
    if "file" not in request.files:
        abort(400, description="No file part")
    file = request.files["file"]
    if file.filename == "":
        abort(400, description="No selected file")
    if not allowed_file(file.filename):
        abort(400, description="File type not allowed")
    ext = file.filename.rsplit(".", 1)[1].lower()
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    stored_name = f"{uuid.uuid4().hex}.{ext}"
    path = os.path.join(app.config["UPLOAD_FOLDER"], stored_name)
    file.save(path)
    return jsonify({"filename": stored_name, "path": path}), 201


if __name__ == "__main__":
    app.run(debug=True)