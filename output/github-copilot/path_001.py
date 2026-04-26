import os
import re
import unicodedata
from pathlib import Path

from flask import Flask, abort, send_file

app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent
UPLOADS_DIR = BASE_DIR / "uploads"
UPLOADS_DIR.mkdir(exist_ok=True)
UPLOADS_ROOT = os.path.realpath(str(UPLOADS_DIR))


def _normalize_legacy_segment(segment: str) -> str:
    normalized = unicodedata.normalize("NFKD", segment)
    normalized = normalized.encode("ascii", "ignore").decode("ascii")
    normalized = re.sub(r"[\s\-]+", "_", normalized)
    normalized = re.sub(r"[^\w.]", "", normalized)
    normalized = re.sub(r"_+", "_", normalized)
    return normalized.strip("._").lower()


def _legacy_candidates(filename: str) -> list[str]:
    if "\x00" in filename:
        return []

    raw_parts = filename.replace("\\", "/").split("/")
    parts = [part for part in raw_parts if part not in ("", ".")]

    if not parts or any(part == ".." for part in parts):
        return []

    exact = "/".join(parts)
    legacy = "/".join(_normalize_legacy_segment(part) for part in parts)

    if not legacy or any(not _normalize_legacy_segment(part) for part in parts):
        return [exact]

    return [exact] if legacy == exact else [exact, legacy]


def _safe_resolve(relative_path: str) -> Path | None:
    candidate = os.path.realpath(os.path.join(UPLOADS_ROOT, relative_path))
    if candidate != UPLOADS_ROOT and not candidate.startswith(UPLOADS_ROOT + os.sep):
        return None

    resolved_path = Path(candidate)
    if not resolved_path.is_file():
        return None

    return resolved_path


@app.route("/uploads/<path:filename>", methods=["GET"])
def serve_upload(filename: str):
    for candidate in _legacy_candidates(filename):
        resolved = _safe_resolve(candidate)
        if resolved is not None:
            return send_file(resolved)

    abort(404)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=False)