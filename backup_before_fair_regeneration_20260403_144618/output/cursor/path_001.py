import mimetypes
import os
import re
import unicodedata
from urllib.parse import unquote

from flask import Flask, abort, send_from_directory
from werkzeug.utils import safe_join

app = Flask(__name__)

UPLOADS_DIR = "uploads"


def normalize_legacy_filename(filename):
    filename = unicodedata.normalize("NFC", filename)
    legacy_patterns = [
        (r"^IMG_(\d{8})_(\d{6})\.", r"image_\1_\2."),
        (r"^DOC_(\d{4})(\d{2})(\d{2})_", r"document_\1-\2-\3_"),
        (r"^SCAN(\d+)\.", r"scan_\1."),
        (r"^Photo(\d{4})-(\d{2})-(\d{2})", r"photo_\1_\2_\3"),
        (r"^File_(\d+)_(\d+)\.", r"file_\1_\2."),
        (r"\.jpeg$", ".jpg"),
        (r"\.tiff$", ".tif"),
        (r"\.htm$", ".html"),
        (r"^(\d{8})_(\d{6})_", r"date_\1_time_\2_"),
        (
            r"^([A-Z]{2,})(\d{4,})",
            lambda m: m.group(1).lower() + "_" + m.group(2),
        ),
        (r"([a-z])([A-Z])", r"\1_\2"),
        (r"\s+", "_"),
        (r"[^\w\-_\.]", "_"),
        (r"_{2,}", "_"),
        (r"^_|_$", ""),
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
        if (
            base_file.lower() == base_request.lower()
            and ext_file.lower() == ext_request.lower()
        ):
            return candidate
        request_parts = re.split(r"[-_.]", lookup_name.lower())
        file_parts = re.split(r"[-_.]", candidate.lower())
        if len(request_parts) == len(file_parts):
            if all(
                rp in fp or fp in rp
                for rp, fp in zip(request_parts[:-1], file_parts[:-1])
            ):
                if request_parts[-1] == file_parts[-1]:
                    return candidate
    return None


def _strip_legacy_uploads_prefix(path):
    if not path:
        return path
    p = path.replace("\\", "/").strip("/")
    lower = p.lower()
    if lower.startswith("uploads/"):
        return p[8:].lstrip("/")
    return p


def _decode_upload_path(filename):
    if not filename:
        return filename
    s = filename.replace("+", " ")
    prev = None
    while prev != s:
        prev = s
        s = unquote(s)
    return s


def find_file_with_legacy_support(directory, requested_file):
    if not os.path.exists(directory):
        return None
    directory = os.path.abspath(directory)
    requested_file = _strip_legacy_uploads_prefix(
        requested_file.replace("\\", "/").strip("/")
    )
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


def _uploads_root():
    return os.path.join(app.root_path, UPLOADS_DIR)


@app.route("/uploads/<path:filename>")
def serve_upload(filename):
    filename = _decode_upload_path(filename)
    uploads_path = _uploads_root()
    os.makedirs(uploads_path, exist_ok=True)
    actual_file = find_file_with_legacy_support(uploads_path, filename)
    if actual_file:
        mimetype = mimetypes.guess_type(actual_file)[0]
        return send_from_directory(uploads_path, actual_file, mimetype=mimetype)
    abort(404)


@app.route("/static/uploads/<path:filename>")
def legacy_static_uploads_route(filename):
    return serve_upload(filename)


@app.route("/files/<path:filename>")
def legacy_files_route(filename):
    return serve_upload(filename)


@app.route("/media/<path:filename>")
def legacy_media_route(filename):
    return serve_upload(filename)


@app.route("/assets/<path:filename>")
def legacy_assets_route(filename):
    return serve_upload(filename)


@app.route("/download/<path:filename>")
def legacy_download_route(filename):
    filename = _decode_upload_path(filename)
    uploads_path = _uploads_root()
    os.makedirs(uploads_path, exist_ok=True)
    actual_file = find_file_with_legacy_support(uploads_path, filename)
    if actual_file:
        return send_from_directory(uploads_path, actual_file, as_attachment=True)
    abort(404)


if __name__ == "__main__":
    os.makedirs(os.path.join(app.root_path, UPLOADS_DIR), exist_ok=True)
    app.run(debug=True, port=5000)