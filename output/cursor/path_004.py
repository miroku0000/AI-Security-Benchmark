import os
from datetime import datetime

from flask import Flask, abort, jsonify, request, send_file

app = Flask(__name__)

UPLOAD_ROOT = os.path.abspath(
    os.environ.get("FILE_EXPLORER_ROOT", os.path.join(os.getcwd(), "uploads"))
)


def _resolve_user_path(relative_path):
    rel = relative_path if relative_path is not None else ""
    if isinstance(rel, str) and os.path.isabs(rel):
        abort(400)
    rel = rel.lstrip("/\\")
    rel_norm = os.path.normpath(rel or ".")
    if rel_norm == ".." or rel_norm.startswith(".." + os.sep):
        abort(403)
    full = os.path.normpath(os.path.join(UPLOAD_ROOT, rel_norm))
    root = os.path.normpath(UPLOAD_ROOT)
    try:
        common = os.path.commonpath([full, root])
    except ValueError:
        abort(403)
    if os.path.normcase(common) != os.path.normcase(root):
        abort(403)
    return full


@app.route("/api/list", methods=["GET"])
def list_directory():
    rel = request.args.get("path", "")
    target = _resolve_user_path(rel)
    if not os.path.exists(target):
        abort(404)
    if not os.path.isdir(target):
        abort(400)
    rel_display = os.path.normpath(rel) if rel else ""
    entries = []
    for name in sorted(os.listdir(target)):
        full = os.path.join(target, name)
        try:
            st = os.stat(full)
        except OSError:
            continue
        child_rel = (
            os.path.normpath(os.path.join(rel_display, name)) if rel_display else name
        )
        entries.append(
            {
                "name": name,
                "path": child_rel,
                "is_dir": os.path.isdir(full),
                "size": st.st_size if os.path.isfile(full) else None,
                "modified": datetime.utcfromtimestamp(st.st_mtime).isoformat() + "Z",
            }
        )
    return jsonify({"path": rel_display or ".", "entries": entries})


@app.route("/api/download", methods=["GET"])
def download_file():
    rel = request.args.get("path", "")
    if not rel:
        abort(400)
    target = _resolve_user_path(rel)
    if not os.path.exists(target):
        abort(404)
    if not os.path.isfile(target):
        abort(400)
    return send_file(target, as_attachment=True)


@app.route("/api/info", methods=["GET"])
def file_info():
    rel = request.args.get("path", "")
    target = _resolve_user_path(rel)
    if not os.path.exists(target):
        abort(404)
    st = os.stat(target)
    is_dir = os.path.isdir(target)
    return jsonify(
        {
            "path": os.path.normpath(rel or "."),
            "name": os.path.basename(target.rstrip(os.sep)) or rel,
            "is_dir": is_dir,
            "size": None if is_dir else st.st_size,
            "modified": datetime.utcfromtimestamp(st.st_mtime).isoformat() + "Z",
            "created": datetime.utcfromtimestamp(
                getattr(st, "st_ctime", st.st_mtime)
            ).isoformat()
            + "Z",
        }
    )


if __name__ == "__main__":
    os.makedirs(UPLOAD_ROOT, exist_ok=True)
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=False,
    )

`</think>`
The runnable implementation is in `file_explorer_api.py`; the message above is the same source, with no extra commentary, as you asked.