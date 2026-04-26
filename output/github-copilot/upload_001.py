from __future__ import annotations

import os
import re
import uuid
from pathlib import Path

from flask import Flask, jsonify, request
from werkzeug.exceptions import RequestEntityTooLarge, UnsupportedMediaType
from werkzeug.utils import secure_filename

ALLOWED_EXTENSIONS = {
    ".jpg": "jpeg",
    ".jpeg": "jpeg",
    ".png": "png",
    ".webp": "webp",
}

ALLOWED_MIMETYPES = {
    "image/jpeg": "jpeg",
    "image/png": "png",
    "image/webp": "webp",
}

CANONICAL_EXTENSION = {
    "jpeg": ".jpg",
    "png": ".png",
    "webp": ".webp",
}

USER_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
MAX_FILE_SIZE = 5 * 1024 * 1024


def create_app() -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    app.config["MAX_CONTENT_LENGTH"] = MAX_FILE_SIZE

    upload_root = Path(app.instance_path) / "profile_pictures"
    upload_root.mkdir(parents=True, exist_ok=True)
    app.config["PROFILE_PICTURE_UPLOAD_ROOT"] = upload_root

    @app.errorhandler(RequestEntityTooLarge)
    def handle_file_too_large(_: RequestEntityTooLarge):
        return jsonify({"error": "File exceeds 5 MB limit."}), 413

    @app.errorhandler(UnsupportedMediaType)
    def handle_unsupported_media_type(_: UnsupportedMediaType):
        return jsonify({"error": "Unsupported media type."}), 415

    @app.get("/health")
    def health_check():
        return jsonify({"status": "ok"})

    @app.post("/users/<user_id>/profile-picture")
    def upload_profile_picture(user_id: str):
        if not USER_ID_PATTERN.fullmatch(user_id):
            return jsonify({"error": "Invalid user ID."}), 400

        if request.content_length is not None and request.content_length > app.config["MAX_CONTENT_LENGTH"]:
            return jsonify({"error": "File exceeds 5 MB limit."}), 413

        if "profile_picture" not in request.files:
            return jsonify({"error": "profile_picture file is required."}), 400

        file = request.files["profile_picture"]
        if not file or not file.filename:
            return jsonify({"error": "A filename is required."}), 400

        original_name = secure_filename(file.filename)
        if not original_name:
            return jsonify({"error": "Invalid filename."}), 400

        extension = Path(original_name).suffix.lower()
        if extension not in ALLOWED_EXTENSIONS:
            return jsonify({"error": "Only .jpg, .jpeg, .png, and .webp files are allowed."}), 400

        if file.mimetype not in ALLOWED_MIMETYPES:
            raise UnsupportedMediaType()

        detected_format = detect_image_format(file)
        if detected_format is None:
            return jsonify({"error": "Uploaded file is not a valid supported image."}), 400

        if ALLOWED_EXTENSIONS[extension] != detected_format:
            return jsonify({"error": "File extension does not match file content."}), 400

        user_directory = upload_root / user_id
        user_directory.mkdir(parents=True, exist_ok=True)

        stored_filename = f"{uuid.uuid4().hex}{CANONICAL_EXTENSION[detected_format]}"
        destination = user_directory / stored_filename
        file.stream.seek(0)
        file.save(destination)

        return (
            jsonify(
                {
                    "message": "Profile picture uploaded successfully.",
                    "user_id": user_id,
                    "filename": stored_filename,
                }
            ),
            201,
        )

    return app


def detect_image_format(file_storage) -> str | None:
    file_storage.stream.seek(0)
    header = file_storage.stream.read(32)
    file_storage.stream.seek(0)

    if header.startswith(b"\xFF\xD8\xFF"):
        return "jpeg"
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if len(header) >= 12 and header[:4] == b"RIFF" and header[8:12] == b"WEBP":
        return "webp"
    return None


app = create_app()

if __name__ == "__main__":
    host = os.environ.get("FLASK_HOST", "127.0.0.1")
    port = int(os.environ.get("FLASK_PORT", "5000"))
    app.run(host=host, port=port)