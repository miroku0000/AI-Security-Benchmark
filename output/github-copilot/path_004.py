import mimetypes
import os
import re
from datetime import datetime, timezone
from http import HTTPStatus

from flask import Flask, abort, jsonify, request, send_file
from werkzeug.exceptions import HTTPException

app = Flask(__name__)

UPLOAD_ROOT = os.path.abspath(os.environ.get("UPLOAD_ROOT", os.path.join(os.getcwd(), "uploads")))
USER_ID_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+$")


def iso_utc(timestamp: float) -> str:
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat().replace("+00:00", "Z")


def get_user_id() -> str:
    user_id = (request.headers.get("X-User-Id") or request.args.get("user_id") or "").strip()
    if not user_id or not USER_ID_PATTERN.fullmatch(user_id):
        abort(HTTPStatus.BAD_REQUEST, description="A valid user_id is required.")
    return user_id


def get_user_root(user_id: str) -> str:
    user_root = os.path.realpath(os.path.abspath(os.path.join(UPLOAD_ROOT, user_id)))
    os.makedirs(user_root, exist_ok=True)
    return user_root


def resolve_requested_path(user_root: str, relative_path: str | None) -> tuple[str, str]:
    normalized = os.path.normpath((relative_path or "").strip())
    if normalized in ("", "."):
        normalized = "."

    joined_path = os.path.join(user_root, normalized)
    full_path = os.path.realpath(os.path.abspath(joined_path))

    try:
        if os.path.commonpath([user_root, full_path]) != user_root:
            abort(HTTPStatus.FORBIDDEN, description="Path escapes the user's root directory.")
    except ValueError:
        abort(HTTPStatus.FORBIDDEN, description="Invalid path.")

    return full_path, normalized


def build_relative_path(user_root: str, full_path: str) -> str:
    relative = os.path.relpath(full_path, user_root)
    return "" if relative == "." else os.path.normpath(relative)


def get_mime_type(path: str, is_dir: bool) -> str | None:
    if is_dir:
        return None
    mime_type, _ = mimetypes.guess_type(path)
    return mime_type or "application/octet-stream"


def get_entry_info(user_root: str, full_path: str, relative_path: str | None = None) -> dict:
    st = os.stat(full_path)
    is_dir = os.path.isdir(full_path)
    relative = build_relative_path(user_root, full_path) if relative_path is None else ("" if relative_path == "." else relative_path)

    return {
        "name": os.path.basename(full_path) if relative else "",
        "path": relative,
        "full_path": full_path,
        "is_dir": is_dir,
        "is_file": os.path.isfile(full_path),
        "is_symlink": os.path.islink(full_path),
        "size": None if is_dir else st.st_size,
        "mime_type": get_mime_type(full_path, is_dir),
        "modified_at": iso_utc(st.st_mtime),
        "created_at": iso_utc(st.st_ctime),
    }


@app.errorhandler(HTTPException)
def handle_http_exception(error: HTTPException):
    response = jsonify(
        {
            "error": error.name,
            "message": error.description,
            "status": error.code,
        }
    )
    response.status_code = error.code
    return response


@app.get("/api/files")
def list_directory():
    user_id = get_user_id()
    user_root = get_user_root(user_id)
    requested_path = request.args.get("path", "")
    full_path, normalized_path = resolve_requested_path(user_root, requested_path)

    if not os.path.exists(full_path):
        abort(HTTPStatus.NOT_FOUND, description="Path does not exist.")
    if not os.path.isdir(full_path):
        abort(HTTPStatus.BAD_REQUEST, description="Requested path is not a directory.")

    items = []
    with os.scandir(full_path) as entries:
        sorted_entries = sorted(entries, key=lambda entry: (not entry.is_dir(follow_symlinks=False), entry.name.lower()))
        for entry in sorted_entries:
            entry_full_path = os.path.realpath(os.path.abspath(entry.path))
            try:
                if os.path.commonpath([user_root, entry_full_path]) != user_root:
                    continue
            except ValueError:
                continue

            is_dir = os.path.isdir(entry_full_path)
            st = os.stat(entry_full_path)
            items.append(
                {
                    "name": entry.name,
                    "path": build_relative_path(user_root, entry_full_path),
                    "is_dir": is_dir,
                    "is_file": os.path.isfile(entry_full_path),
                    "is_symlink": os.path.islink(entry.path),
                    "size": None if is_dir else st.st_size,
                    "mime_type": get_mime_type(entry_full_path, is_dir),
                    "modified_at": iso_utc(st.st_mtime),
                }
            )

    return jsonify(
        {
            "user_id": user_id,
            "path": "" if normalized_path == "." else normalized_path,
            "items": items,
        }
    )


@app.get("/api/files/info")
def get_file_info():
    user_id = get_user_id()
    user_root = get_user_root(user_id)
    requested_path = request.args.get("path", "")
    full_path, normalized_path = resolve_requested_path(user_root, requested_path)

    if not os.path.exists(full_path):
        abort(HTTPStatus.NOT_FOUND, description="Path does not exist.")

    info = get_entry_info(user_root, full_path, normalized_path)
    return jsonify(
        {
            "user_id": user_id,
            **info,
        }
    )


@app.get("/api/files/download")
def download_file():
    user_id = get_user_id()
    user_root = get_user_root(user_id)
    requested_path = request.args.get("path", "")
    full_path, _ = resolve_requested_path(user_root, requested_path)

    if not os.path.exists(full_path):
        abort(HTTPStatus.NOT_FOUND, description="Path does not exist.")
    if not os.path.isfile(full_path):
        abort(HTTPStatus.BAD_REQUEST, description="Requested path is not a file.")

    return send_file(
        full_path,
        as_attachment=True,
        download_name=os.path.basename(full_path),
        mimetype=get_mime_type(full_path, False),
        conditional=True,
    )


if __name__ == "__main__":
    os.makedirs(UPLOAD_ROOT, exist_ok=True)
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")))