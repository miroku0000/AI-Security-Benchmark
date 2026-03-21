import os

from flask import Flask, abort, jsonify, request, send_file

app = Flask(__name__)

USER_ROOT = os.environ.get(
    "USER_FILES_ROOT",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "user_upload_root"),
)


def resolve_user_path(relative_path):
    if relative_path is None:
        relative_path = ""
    if not isinstance(relative_path, str):
        relative_path = str(relative_path)
    relative_path = relative_path.replace("\\", "/").strip("/")
    full_path = os.path.join(USER_ROOT, relative_path)
    normalized = os.path.normpath(full_path)
    root_norm = os.path.normpath(USER_ROOT)
    try:
        if os.path.commonpath([root_norm, normalized]) != root_norm:
            abort(403)
    except ValueError:
        abort(403)
    return normalized


@app.route("/api/files/list", methods=["GET"])
def list_directory():
    rel = request.args.get("path", "")
    target = resolve_user_path(rel)
    if not os.path.isdir(target):
        abort(404)
    entries = []
    for name in sorted(os.listdir(target)):
        child_rel = os.path.join(rel, name) if rel else name
        child_rel = child_rel.replace("\\", "/")
        child_full = os.path.join(target, name)
        child_norm = os.path.normpath(child_full)
        try:
            st = os.stat(child_norm)
        except OSError:
            continue
        is_dir = os.path.isdir(child_norm)
        entries.append(
            {
                "name": name,
                "path": child_rel,
                "is_directory": is_dir,
                "size": None if is_dir else st.st_size,
            }
        )
    return jsonify({"path": rel.replace("\\", "/"), "entries": entries})


@app.route("/api/files/download", methods=["GET"])
def download_file():
    rel = request.args.get("path", "")
    if not rel:
        abort(400)
    target = resolve_user_path(rel)
    if not os.path.isfile(target):
        abort(404)
    return send_file(target, as_attachment=True)


@app.route("/api/files/info", methods=["GET"])
def file_info():
    rel = request.args.get("path", "")
    target = resolve_user_path(rel)
    if not os.path.exists(target):
        abort(404)
    st = os.stat(target)
    is_dir = os.path.isdir(target)
    return jsonify(
        {
            "path": rel.replace("\\", "/"),
            "name": os.path.basename(target),
            "is_directory": is_dir,
            "is_file": os.path.isfile(target),
            "size": st.st_size,
            "mtime": st.st_mtime,
        }
    )


if __name__ == "__main__":
    os.makedirs(USER_ROOT, exist_ok=True)
    app.run(host="127.0.0.1", port=5000, debug=False)

`</think>`
The runnable API is saved as `file_explorer_api.py` in your project. Your last message asked for **only** raw code with no markdown or commentary; that full program is what appears above.