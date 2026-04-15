"""
Crowdsourced Data Labeling System
Accept image labels from multiple annotators via REST API.
Aggregate labels using majority voting. Train model on labeled data.
"""

import os
import json
import sqlite3
import hashlib
import secrets
from collections import Counter
from datetime import datetime, timedelta
from functools import wraps
from io import BytesIO

from flask import Flask, request, jsonify, g
from werkzeug.utils import secure_filename
from PIL import Image
import numpy as np

app = Flask(__name__)
app.config["DATABASE"] = os.environ.get("DB_PATH", "labeling.db")
app.config["UPLOAD_FOLDER"] = os.environ.get("UPLOAD_FOLDER", "uploads")
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB max upload
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", secrets.token_hex(32))
app.config["MIN_ANNOTATIONS"] = int(os.environ.get("MIN_ANNOTATIONS", "3"))
app.config["ALLOWED_EXTENSIONS"] = {"png", "jpg", "jpeg", "gif", "bmp", "webp"}

os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)


# ── Database ─────────────────────────────────────────────────────────

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA journal_mode=WAL")
        g.db.execute("PRAGMA foreign_keys=ON")
    return g.db


@app.teardown_appcontext
def close_db(exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = get_db()
    db.executescript("""
        CREATE TABLE IF NOT EXISTS annotators (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            api_key_hash TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            is_active INTEGER NOT NULL DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            original_name TEXT NOT NULL,
            file_hash TEXT UNIQUE NOT NULL,
            uploaded_at TEXT NOT NULL DEFAULT (datetime('now')),
            consensus_label TEXT,
            consensus_confidence REAL
        );
        CREATE TABLE IF NOT EXISTS labels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            image_id INTEGER NOT NULL,
            annotator_id INTEGER NOT NULL,
            label TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (image_id) REFERENCES images(id),
            FOREIGN KEY (annotator_id) REFERENCES annotators(id),
            UNIQUE(image_id, annotator_id)
        );
        CREATE TABLE IF NOT EXISTS label_classes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        );
        CREATE TABLE IF NOT EXISTS training_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            started_at TEXT NOT NULL DEFAULT (datetime('now')),
            completed_at TEXT,
            num_samples INTEGER,
            num_classes INTEGER,
            accuracy REAL,
            status TEXT NOT NULL DEFAULT 'running'
        );
        CREATE INDEX IF NOT EXISTS idx_labels_image ON labels(image_id);
        CREATE INDEX IF NOT EXISTS idx_labels_annotator ON labels(annotator_id);
        CREATE INDEX IF NOT EXISTS idx_images_consensus ON images(consensus_label);
    """)
    db.commit()


with app.app_context():
    init_db()


# ── Auth ─────────────────────────────────────────────────────────────

def hash_api_key(key):
    return hashlib.sha256(key.encode()).hexdigest()


def require_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get("X-API-Key", "")
        if not api_key:
            return jsonify({"error": "Missing X-API-Key header"}), 401
        db = get_db()
        row = db.execute(
            "SELECT id, username FROM annotators WHERE api_key_hash = ? AND is_active = 1",
            (hash_api_key(api_key),),
        ).fetchone()
        if row is None:
            return jsonify({"error": "Invalid or inactive API key"}), 401
        g.annotator_id = row["id"]
        g.annotator_username = row["username"]
        return f(*args, **kwargs)
    return decorated


# ── Helpers ──────────────────────────────────────────────────────────

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in app.config["ALLOWED_EXTENSIONS"]


def file_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def validate_image(data: bytes) -> bool:
    """Verify the bytes are actually a valid image."""
    try:
        img = Image.open(BytesIO(data))
        img.verify()
        return True
    except Exception:
        return False


def compute_consensus(image_id):
    """Majority vote across all annotations for an image."""
    db = get_db()
    rows = db.execute(
        "SELECT label FROM labels WHERE image_id = ?", (image_id,)
    ).fetchall()
    if len(rows) < app.config["MIN_ANNOTATIONS"]:
        return None, None
    counts = Counter(r["label"] for r in rows)
    winner, winner_count = counts.most_common(1)[0]
    confidence = winner_count / len(rows)
    return winner, confidence


def sanitize_label(label_text):
    """Sanitize and validate a label string."""
    if not isinstance(label_text, str):
        return None
    label_text = label_text.strip()
    if not label_text or len(label_text) > 100:
        return None
    # Allow only alphanumeric, spaces, hyphens, underscores
    if not all(c.isalnum() or c in " -_" for c in label_text):
        return None
    return label_text


# ── Routes: Annotator Management ────────────────────────────────────

@app.route("/api/annotators", methods=["POST"])
def register_annotator():
    data = request.get_json(silent=True)
    if not data or "username" not in data:
        return jsonify({"error": "username is required"}), 400

    username = data["username"].strip()
    if not username or len(username) > 50:
        return jsonify({"error": "Invalid username"}), 400
    if not all(c.isalnum() or c in "-_" for c in username):
        return jsonify({"error": "Username must be alphanumeric (hyphens/underscores allowed)"}), 400

    api_key = secrets.token_urlsafe(32)
    db = get_db()
    try:
        db.execute(
            "INSERT INTO annotators (username, api_key_hash) VALUES (?, ?)",
            (username, hash_api_key(api_key)),
        )
        db.commit()
    except sqlite3.IntegrityError:
        return jsonify({"error": "Username already exists"}), 409

    return jsonify({"username": username, "api_key": api_key}), 201


@app.route("/api/annotators", methods=["GET"])
def list_annotators():
    db = get_db()
    rows = db.execute(
        """SELECT a.id, a.username, a.created_at, a.is_active,
                  COUNT(l.id) as label_count
           FROM annotators a LEFT JOIN labels l ON a.id = l.annotator_id
           GROUP BY a.id"""
    ).fetchall()
    return jsonify([dict(r) for r in rows])


# ── Routes: Image Upload ────────────────────────────────────────────

@app.route("/api/images", methods=["POST"])
@require_api_key
def upload_image():
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    f = request.files["file"]
    if not f.filename or not allowed_file(f.filename):
        return jsonify({"error": "Invalid file type"}), 400

    data = f.read()
    if len(data) == 0:
        return jsonify({"error": "Empty file"}), 400

    if not validate_image(data):
        return jsonify({"error": "File is not a valid image"}), 400

    fhash = file_hash(data)
    safe_name = secure_filename(f.filename)
    stored_name = f"{fhash}_{safe_name}"
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], stored_name)

    db = get_db()
    existing = db.execute("SELECT id FROM images WHERE file_hash = ?", (fhash,)).fetchone()
    if existing:
        return jsonify({"error": "Duplicate image", "image_id": existing["id"]}), 409

    with open(filepath, "wb") as out:
        out.write(data)

    db.execute(
        "INSERT INTO images (filename, original_name, file_hash) VALUES (?, ?, ?)",
        (stored_name, safe_name, fhash),
    )
    db.commit()

    row = db.execute("SELECT id FROM images WHERE file_hash = ?", (fhash,)).fetchone()
    return jsonify({"image_id": row["id"], "filename": stored_name}), 201


@app.route("/api/images", methods=["GET"])
def list_images():
    db = get_db()
    unlabeled_only = request.args.get("unlabeled", "").lower() == "true"
    page = max(1, int(request.args.get("page", 1)))
    per_page = min(100, max(1, int(request.args.get("per_page", 20))))
    offset = (page - 1) * per_page

    if unlabeled_only:
        rows = db.execute(
            """SELECT id, original_name, uploaded_at, consensus_label, consensus_confidence
               FROM images WHERE consensus_label IS NULL
               ORDER BY uploaded_at LIMIT ? OFFSET ?""",
            (per_page, offset),
        ).fetchall()
    else:
        rows = db.execute(
            """SELECT id, original_name, uploaded_at, consensus_label, consensus_confidence
               FROM images ORDER BY uploaded_at LIMIT ? OFFSET ?""",
            (per_page, offset),
        ).fetchall()

    return jsonify([dict(r) for r in rows])


# ── Routes: Labeling ────────────────────────────────────────────────

@app.route("/api/images/<int:image_id>/labels", methods=["POST"])
@require_api_key
def submit_label(image_id):
    db = get_db()
    image = db.execute("SELECT id FROM images WHERE id = ?", (image_id,)).fetchone()
    if image is None:
        return jsonify({"error": "Image not found"}), 404

    data = request.get_json(silent=True)
    if not data or "label" not in data:
        return jsonify({"error": "label is required"}), 400

    label = sanitize_label(data["label"])
    if label is None:
        return jsonify({"error": "Invalid label (alphanumeric, max 100 chars)"}), 400

    # Ensure label class exists
    db.execute("INSERT OR IGNORE INTO label_classes (name) VALUES (?)", (label,))

    try:
        db.execute(
            "INSERT INTO labels (image_id, annotator_id, label) VALUES (?, ?, ?)",
            (image_id, g.annotator_id, label),
        )
    except sqlite3.IntegrityError:
        return jsonify({"error": "You have already labeled this image"}), 409

    # Recompute consensus
    consensus, confidence = compute_consensus(image_id)
    if consensus is not None:
        db.execute(
            "UPDATE images SET consensus_label = ?, consensus_confidence = ? WHERE id = ?",
            (consensus, confidence, image_id),
        )

    db.commit()
    return jsonify({
        "image_id": image_id,
        "label": label,
        "consensus_label": consensus,
        "consensus_confidence": confidence,
    }), 201


@app.route("/api/images/<int:image_id>/labels", methods=["GET"])
def get_labels(image_id):
    db = get_db()
    image = db.execute(
        "SELECT id, consensus_label, consensus_confidence FROM images WHERE id = ?",
        (image_id,),
    ).fetchone()
    if image is None:
        return jsonify({"error": "Image not found"}), 404

    labels = db.execute(
        """SELECT l.label, a.username, l.created_at
           FROM labels l JOIN annotators a ON l.annotator_id = a.id
           WHERE l.image_id = ?""",
        (image_id,),
    ).fetchall()

    return jsonify({
        "image_id": image_id,
        "consensus_label": image["consensus_label"],
        "consensus_confidence": image["consensus_confidence"],
        "annotations": [dict(l) for l in labels],
    })


# ── Routes: Label Classes ───────────────────────────────────────────

@app.route("/api/label-classes", methods=["GET"])
def list_label_classes():
    db = get_db()
    rows = db.execute(
        """SELECT lc.name, COUNT(l.id) as usage_count
           FROM label_classes lc LEFT JOIN labels l ON lc.name = l.label
           GROUP BY lc.name ORDER BY usage_count DESC"""
    ).fetchall()
    return jsonify([dict(r) for r in rows])


@app.route("/api/label-classes", methods=["POST"])
@require_api_key
def add_label_class():
    data = request.get_json(silent=True)
    if not data or "name" not in data:
        return jsonify({"error": "name is required"}), 400
    name = sanitize_label(data["name"])
    if name is None:
        return jsonify({"error": "Invalid label class name"}), 400
    db = get_db()
    try:
        db.execute("INSERT INTO label_classes (name) VALUES (?)", (name,))
        db.commit()
    except sqlite3.IntegrityError:
        return jsonify({"error": "Label class already exists"}), 409
    return jsonify({"name": name}), 201


# ── Routes: Consensus & Stats ───────────────────────────────────────

@app.route("/api/consensus", methods=["GET"])
def get_consensus_data():
    """Return all images that have reached consensus."""
    db = get_db()
    min_confidence = float(request.args.get("min_confidence", 0.0))
    rows = db.execute(
        """SELECT id, original_name, consensus_label, consensus_confidence
           FROM images
           WHERE consensus_label IS NOT NULL AND consensus_confidence >= ?
           ORDER BY consensus_confidence DESC""",
        (min_confidence,),
    ).fetchall()
    return jsonify([dict(r) for r in rows])


@app.route("/api/stats", methods=["GET"])
def get_stats():
    db = get_db()
    total_images = db.execute("SELECT COUNT(*) as c FROM images").fetchone()["c"]
    labeled_images = db.execute(
        "SELECT COUNT(*) as c FROM images WHERE consensus_label IS NOT NULL"
    ).fetchone()["c"]
    total_annotations = db.execute("SELECT COUNT(*) as c FROM labels").fetchone()["c"]
    total_annotators = db.execute(
        "SELECT COUNT(*) as c FROM annotators WHERE is_active = 1"
    ).fetchone()["c"]

    class_dist = db.execute(
        """SELECT consensus_label as label, COUNT(*) as count
           FROM images WHERE consensus_label IS NOT NULL
           GROUP BY consensus_label ORDER BY count DESC"""
    ).fetchall()

    return jsonify({
        "total_images": total_images,
        "labeled_images": labeled_images,
        "unlabeled_images": total_images - labeled_images,
        "total_annotations": total_annotations,
        "active_annotators": total_annotators,
        "class_distribution": [dict(r) for r in class_dist],
    })


# ── Routes: Training ────────────────────────────────────────────────

@app.route("/api/train", methods=["POST"])
@require_api_key
def train_model():
    """Train a simple model on consensus-labeled data."""
    db = get_db()

    rows = db.execute(
        """SELECT i.id, i.filename, i.consensus_label
           FROM images i
           WHERE i.consensus_label IS NOT NULL"""
    ).fetchall()

    if len(rows) < 2:
        return jsonify({"error": "Need at least 2 labeled images to train"}), 400

    labels = list(set(r["consensus_label"] for r in rows))
    if len(labels) < 2:
        return jsonify({"error": "Need at least 2 distinct classes to train"}), 400

    label_to_idx = {l: i for i, l in enumerate(labels)}

    run = db.execute(
        "INSERT INTO training_runs (num_samples, num_classes) VALUES (?, ?)",
        (len(rows), len(labels)),
    )
    run_id = run.lastrowid
    db.commit()

    # Load images and resize to uniform dimensions
    X = []
    y = []
    img_size = 32
    for row in rows:
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], row["filename"])
        if not os.path.isfile(filepath):
            continue
        try:
            img = Image.open(filepath).convert("RGB").resize((img_size, img_size))
            arr = np.array(img, dtype=np.float32).flatten() / 255.0
            X.append(arr)
            y.append(label_to_idx[row["consensus_label"]])
        except Exception:
            continue

    if len(X) < 2:
        db.execute(
            "UPDATE training_runs SET status = 'failed', completed_at = datetime('now') WHERE id = ?",
            (run_id,),
        )
        db.commit()
        return jsonify({"error": "Not enough valid images to train"}), 400

    X = np.array(X)
    y = np.array(y)

    # Simple softmax classifier via gradient descent
    num_features = X.shape[1]
    num_classes = len(labels)
    W = np.random.randn(num_features, num_classes) * 0.01
    b = np.zeros(num_classes)
    lr = 0.1
    epochs = 50

    for _ in range(epochs):
        logits = X @ W + b
        # Numerically stable softmax
        logits -= logits.max(axis=1, keepdims=True)
        exp_logits = np.exp(logits)
        probs = exp_logits / exp_logits.sum(axis=1, keepdims=True)

        # Cross-entropy gradient
        one_hot = np.zeros_like(probs)
        one_hot[np.arange(len(y)), y] = 1
        grad = probs - one_hot

        W -= lr * (X.T @ grad) / len(y)
        b -= lr * grad.mean(axis=0)

    # Compute training accuracy
    preds = (X @ W + b).argmax(axis=1)
    accuracy = float((preds == y).mean())

    db.execute(
        "UPDATE training_runs SET status = 'completed', completed_at = datetime('now'), accuracy = ? WHERE id = ?",
        (accuracy, run_id),
    )
    db.commit()

    # Save model weights
    model_path = os.path.join(app.config["UPLOAD_FOLDER"], f"model_run_{run_id}.npz")
    np.savez(model_path, W=W, b=b, labels=labels, img_size=img_size)

    return jsonify({
        "run_id": run_id,
        "num_samples": len(X),
        "num_classes": num_classes,
        "classes": labels,
        "training_accuracy": accuracy,
        "model_path": model_path,
    })


@app.route("/api/training-runs", methods=["GET"])
def list_training_runs():
    db = get_db()
    rows = db.execute(
        "SELECT * FROM training_runs ORDER BY started_at DESC"
    ).fetchall()
    return jsonify([dict(r) for r in rows])


# ── Routes: Prediction ──────────────────────────────────────────────

@app.route("/api/predict/<int:run_id>", methods=["POST"])
def predict(run_id):
    """Use a trained model to predict label for an uploaded image."""
    model_path = os.path.join(app.config["UPLOAD_FOLDER"], f"model_run_{run_id}.npz")
    if not os.path.isfile(model_path):
        return jsonify({"error": "Model not found"}), 404

    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    f = request.files["file"]
    if not f.filename or not allowed_file(f.filename):
        return jsonify({"error": "Invalid file type"}), 400

    data = f.read()
    if not validate_image(data):
        return jsonify({"error": "Invalid image"}), 400

    model = np.load(model_path, allow_pickle=True)
    W = model["W"]
    b = model["b"]
    labels = model["labels"].tolist()
    img_size = int(model["img_size"])

    img = Image.open(BytesIO(data)).convert("RGB").resize((img_size, img_size))
    arr = np.array(img, dtype=np.float32).flatten() / 255.0

    logits = arr @ W + b
    logits -= logits.max()
    exp_logits = np.exp(logits)
    probs = exp_logits / exp_logits.sum()

    pred_idx = int(probs.argmax())
    return jsonify({
        "predicted_label": labels[pred_idx],
        "confidence": float(probs[pred_idx]),
        "all_probabilities": {labels[i]: float(probs[i]) for i in range(len(labels))},
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(host="127.0.0.1", port=port, debug=debug)