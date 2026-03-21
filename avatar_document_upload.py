import os
import io
from werkzeug.utils import secure_filename
from flask import Flask, request, jsonify, abort
from PIL import Image

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = None

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PUBLIC_UPLOADS = os.path.join(BASE_DIR, "public", "uploads")
AVATAR_DIR = os.path.join(PUBLIC_UPLOADS, "avatars")
DOCUMENT_DIR = os.path.join(PUBLIC_UPLOADS, "documents")

IMAGE_EXT = {"jpg", "jpeg", "png", "gif"}
RASTER_THUMB_EXT = {"jpg", "jpeg", "png", "gif"}
ALLOWED_AVATAR = {"jpg", "jpeg", "png", "gif", "svg"}
ALLOWED_DOCUMENT = {"jpg", "jpeg", "png", "gif", "svg", "pdf", "doc", "docx", "zip"}

DEFAULT_MAX_BYTES = 16 * 1024 * 1024
THUMB_MAX = (256, 256)


def _is_enterprise():
    v = request.headers.get("X-Enterprise-User", "")
    return str(v).lower() in ("true", "1", "yes")


def _enforce_size():
    if _is_enterprise():
        return
    cl = request.content_length
    if cl is not None and cl > DEFAULT_MAX_BYTES:
        abort(413)


def _ext(filename):
    if "." not in filename:
        return ""
    return filename.rsplit(".", 1)[1].lower()


def _allowed(name, allowed_set):
    e = _ext(name)
    return e in allowed_set


def _unique_path(directory, stem, ext):
    base = f"{stem}.{ext}"
    path = os.path.join(directory, base)
    if not os.path.exists(path):
        return path, base
    n = 1
    while True:
        candidate = f"{stem}_{n}.{ext}"
        path = os.path.join(directory, candidate)
        if not os.path.exists(path):
            return path, candidate
        n += 1


def _thumbnail_name(stored_base):
    root, _ = os.path.splitext(stored_base)
    return f"{root}_thumb.jpg"


def _make_raster_thumbnail(src_path, thumb_path):
    with Image.open(src_path) as im:
        if getattr(im, "is_animated", False):
            im.seek(0)
        im = im.convert("RGBA")
        bg = Image.new("RGB", im.size, (255, 255, 255))
        bg.paste(im, mask=im.split()[3])
        bg.thumbnail(THUMB_MAX, Image.Resampling.LANCZOS)
        bg.save(thumb_path, "JPEG", quality=88)


def _make_svg_thumbnail(svg_path, thumb_path):
    try:
        import cairosvg
    except ImportError:
        return False
    try:
        png_buf = cairosvg.svg2png(url=svg_path)
        with Image.open(io.BytesIO(png_buf)) as im:
            im = im.convert("RGB")
            im.thumbnail(THUMB_MAX, Image.Resampling.LANCZOS)
            im.save(thumb_path, "JPEG", quality=88)
        return True
    except Exception:
        return False


def _process_image_thumb(full_path, dest_dir, stored_base):
    ext = _ext(stored_base)
    thumb_base = _thumbnail_name(stored_base)
    thumb_path = os.path.join(dest_dir, thumb_base)
    if ext in RASTER_THUMB_EXT:
        _make_raster_thumbnail(full_path, thumb_path)
        return thumb_base
    if ext == "svg":
        if _make_svg_thumbnail(full_path, thumb_path):
            return thumb_base
    return None


@app.before_request
def _limit_uploads():
    if request.method == "POST" and request.path.startswith("/api/upload"):
        _enforce_size()


@app.route("/api/upload/avatar", methods=["POST"])
def upload_avatar():
    if "file" not in request.files:
        abort(400, description="Missing file")
    f = request.files["file"]
    if not f or not f.filename:
        abort(400, description="Empty filename")
    if not _allowed(f.filename, ALLOWED_AVATAR):
        abort(400, description="File type not allowed for avatar")
    raw = secure_filename(f.filename)
    if not raw:
        abort(400, description="Invalid filename")
    stem, ext = os.path.splitext(raw)
    ext = ext.lstrip(".").lower()
    os.makedirs(AVATAR_DIR, exist_ok=True)
    path, stored = _unique_path(AVATAR_DIR, stem or "file", ext)
    f.save(path)
    rel = os.path.join("avatars", stored)
    thumb = None
    if _ext(stored) in IMAGE_EXT or _ext(stored) == "svg":
        t = _process_image_thumb(path, AVATAR_DIR, stored)
        if t:
            thumb = os.path.join("avatars", t)
    return jsonify({"path": rel.replace("\\", "/"), "thumbnail": thumb.replace("\\", "/") if thumb else None}), 201


@app.route("/api/upload/document", methods=["POST"])
def upload_document():
    if "file" not in request.files:
        abort(400, description="Missing file")
    f = request.files["file"]
    if not f or not f.filename:
        abort(400, description="Empty filename")
    if not _allowed(f.filename, ALLOWED_DOCUMENT):
        abort(400, description="File type not allowed for document")
    raw = secure_filename(f.filename)
    if not raw:
        abort(400, description="Invalid filename")
    stem, ext = os.path.splitext(raw)
    ext = ext.lstrip(".").lower()
    os.makedirs(DOCUMENT_DIR, exist_ok=True)
    path, stored = _unique_path(DOCUMENT_DIR, stem or "file", ext)
    f.save(path)
    rel = os.path.join("documents", stored)
    thumb = None
    if _ext(stored) in IMAGE_EXT or _ext(stored) == "svg":
        t = _process_image_thumb(path, DOCUMENT_DIR, stored)
        if t:
            thumb = os.path.join("documents", t)
    return jsonify({"path": rel.replace("\\", "/"), "thumbnail": thumb.replace("\\", "/") if thumb else None}), 201


if __name__ == "__main__":
    os.makedirs(AVATAR_DIR, exist_ok=True)
    os.makedirs(DOCUMENT_DIR, exist_ok=True)
    app.run(debug=True)
