import os
import uuid
import hashlib
import logging
import tempfile
import shutil
from pathlib import Path

import numpy as np
import tensorflow as tf
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# --- Security configuration ---
MAX_UPLOAD_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
ALLOWED_EXTENSIONS = {".csv"}
UPLOAD_DIR = Path(tempfile.mkdtemp(prefix="ml_uploads_"))
APPROVED_DIR = Path(tempfile.mkdtemp(prefix="ml_approved_"))
MODEL_DIR = Path(tempfile.mkdtemp(prefix="ml_models_"))
MAX_CSV_ROWS = 50_000
MAX_LABEL_CLASSES = 100
ALLOWED_IMAGE_SHAPE = (28, 28, 1)  # e.g. grayscale 28x28
API_KEYS = os.environ.get("ML_API_KEYS", "").split(",")  # comma-separated valid keys


def require_api_key(f):
    """Authenticate requests via API key header."""
    from functools import wraps

    @wraps(f)
    def decorated(*args, **kwargs):
        key = request.headers.get("X-API-Key", "")
        if not API_KEYS or API_KEYS == [""]:
            logger.warning("No API keys configured — authentication disabled")
        elif key not in API_KEYS:
            return jsonify({"error": "Invalid or missing API key"}), 401
        return f(*args, **kwargs)

    return decorated


def validate_csv(filepath: Path) -> tuple:
    """
    Parse and validate a CSV upload. Returns (features, labels) numpy arrays
    or raises ValueError with a description of the problem.

    Expected format: each row is flattened pixel values followed by an integer label.
    For 28x28 grayscale images, that's 784 pixel columns + 1 label column = 785 columns.
    """
    expected_cols = int(np.prod(ALLOWED_IMAGE_SHAPE)) + 1  # pixels + label

    try:
        raw = np.loadtxt(
            filepath,
            delimiter=",",
            max_rows=MAX_CSV_ROWS + 1,  # +1 to detect oversized files
            dtype=np.float32,
        )
    except Exception as exc:
        raise ValueError(f"Failed to parse CSV as numeric data: {exc}")

    if raw.ndim != 2:
        raise ValueError("CSV must be a 2D table of numeric values")

    if raw.shape[0] > MAX_CSV_ROWS:
        raise ValueError(f"CSV exceeds maximum of {MAX_CSV_ROWS} rows")

    if raw.shape[1] != expected_cols:
        raise ValueError(
            f"Expected {expected_cols} columns (pixels + label), got {raw.shape[1]}"
        )

    labels = raw[:, -1].astype(np.int32)
    features = raw[:, :-1]

    # Validate label range
    unique_labels = np.unique(labels)
    if len(unique_labels) > MAX_LABEL_CLASSES:
        raise ValueError(f"Too many label classes: {len(unique_labels)} > {MAX_LABEL_CLASSES}")
    if np.any(labels < 0):
        raise ValueError("Labels must be non-negative integers")

    # Validate pixel range
    if np.any(features < 0) or np.any(features > 255):
        raise ValueError("Pixel values must be in range [0, 255]")

    # Normalize pixels to [0, 1]
    features = features / 255.0
    features = features.reshape(-1, *ALLOWED_IMAGE_SHAPE)

    return features, labels


def build_model(num_classes: int) -> tf.keras.Model:
    """Build a simple CNN for image classification."""
    model = tf.keras.Sequential([
        tf.keras.layers.Input(shape=ALLOWED_IMAGE_SHAPE),
        tf.keras.layers.Conv2D(32, (3, 3), activation="relu"),
        tf.keras.layers.MaxPooling2D((2, 2)),
        tf.keras.layers.Conv2D(64, (3, 3), activation="relu"),
        tf.keras.layers.MaxPooling2D((2, 2)),
        tf.keras.layers.Flatten(),
        tf.keras.layers.Dense(64, activation="relu"),
        tf.keras.layers.Dropout(0.3),
        tf.keras.layers.Dense(num_classes, activation="softmax"),
    ])
    model.compile(
        optimizer="adam",
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )
    return model


@app.route("/upload", methods=["POST"])
@require_api_key
def upload_training_data():
    """
    Accept a CSV upload for REVIEW. Files go into a staging area and must
    be approved by an admin before they enter the training pipeline.
    This prevents data poisoning from unapproved contributions.
    """
    if "file" not in request.files:
        return jsonify({"error": "No file part in request"}), 400

    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "No file selected"}), 400

    # Validate extension
    safe_name = secure_filename(file.filename)
    ext = Path(safe_name).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        return jsonify({"error": f"Only {ALLOWED_EXTENSIONS} files are accepted"}), 400

    # Enforce size limit by reading in chunks
    submission_id = uuid.uuid4().hex
    dest = UPLOAD_DIR / f"{submission_id}{ext}"
    bytes_written = 0
    sha256 = hashlib.sha256()

    with open(dest, "wb") as out:
        while True:
            chunk = file.stream.read(8192)
            if not chunk:
                break
            bytes_written += len(chunk)
            if bytes_written > MAX_UPLOAD_SIZE_BYTES:
                out.close()
                dest.unlink(missing_ok=True)
                return jsonify({"error": "File exceeds size limit"}), 413
            sha256.update(chunk)
            out.write(chunk)

    # Run validation on content (does NOT add to training set yet)
    try:
        features, labels = validate_csv(dest)
        sample_count = len(labels)
        num_classes = len(np.unique(labels))
    except ValueError as exc:
        dest.unlink(missing_ok=True)
        return jsonify({"error": f"Validation failed: {exc}"}), 422

    logger.info(
        "Submission %s staged: %d samples, %d classes, sha256=%s",
        submission_id, sample_count, num_classes, sha256.hexdigest(),
    )

    return jsonify({
        "submission_id": submission_id,
        "status": "pending_review",
        "samples": sample_count,
        "classes": num_classes,
        "sha256": sha256.hexdigest(),
        "message": "Upload staged for admin review before training.",
    }), 202


@app.route("/admin/approve/<submission_id>", methods=["POST"])
@require_api_key
def approve_submission(submission_id):
    """
    Admin endpoint to approve a staged submission for training.
    In production, add role-based access control here.
    """
    safe_id = secure_filename(submission_id)
    source = UPLOAD_DIR / f"{safe_id}.csv"
    if not source.exists():
        return jsonify({"error": "Submission not found"}), 404

    dest = APPROVED_DIR / f"{safe_id}.csv"
    shutil.move(str(source), str(dest))
    logger.info("Submission %s approved for training", safe_id)

    return jsonify({"submission_id": safe_id, "status": "approved"})


@app.route("/admin/reject/<submission_id>", methods=["POST"])
@require_api_key
def reject_submission(submission_id):
    """Admin endpoint to reject and delete a staged submission."""
    safe_id = secure_filename(submission_id)
    source = UPLOAD_DIR / f"{safe_id}.csv"
    if not source.exists():
        return jsonify({"error": "Submission not found"}), 404

    source.unlink()
    logger.info("Submission %s rejected and deleted", safe_id)
    return jsonify({"submission_id": safe_id, "status": "rejected"})


@app.route("/train", methods=["POST"])
@require_api_key
def train_model():
    """
    Train a model using ONLY approved data. Combines all approved CSVs
    into a single training set.
    """
    approved_files = list(APPROVED_DIR.glob("*.csv"))
    if not approved_files:
        return jsonify({"error": "No approved training data available"}), 400

    all_features = []
    all_labels = []

    for csv_path in approved_files:
        try:
            features, labels = validate_csv(csv_path)
            all_features.append(features)
            all_labels.append(labels)
        except ValueError as exc:
            logger.warning("Skipping corrupted approved file %s: %s", csv_path.name, exc)
            continue

    if not all_features:
        return jsonify({"error": "No valid training data after loading"}), 400

    X = np.concatenate(all_features)
    y = np.concatenate(all_labels)
    num_classes = int(np.max(y) + 1)

    logger.info("Training on %d samples with %d classes", len(y), num_classes)

    model = build_model(num_classes)

    # Use a validation split to detect potential data quality issues
    history = model.fit(
        X, y,
        epochs=10,
        batch_size=32,
        validation_split=0.2,
        verbose=1,
    )

    # Save model
    model_path = MODEL_DIR / "latest_model.keras"
    model.save(str(model_path))

    final_acc = history.history["accuracy"][-1]
    val_acc = history.history["val_accuracy"][-1]

    # Flag suspicious accuracy patterns (potential poisoning indicator)
    if val_acc < 0.1:
        logger.warning(
            "Very low validation accuracy (%.2f) — possible data quality or poisoning issue",
            val_acc,
        )

    return jsonify({
        "status": "complete",
        "total_samples": len(y),
        "num_classes": num_classes,
        "final_accuracy": round(float(final_acc), 4),
        "val_accuracy": round(float(val_acc), 4),
        "model_path": str(model_path),
    })


@app.route("/submissions", methods=["GET"])
@require_api_key
def list_pending():
    """List pending submissions awaiting review."""
    pending = [f.stem for f in UPLOAD_DIR.glob("*.csv")]
    approved = [f.stem for f in APPROVED_DIR.glob("*.csv")]
    return jsonify({"pending": pending, "approved": approved})


if __name__ == "__main__":
    logger.info("Upload dir: %s", UPLOAD_DIR)
    logger.info("Approved dir: %s", APPROVED_DIR)
    logger.info("Model dir: %s", MODEL_DIR)
    logger.info("Set ML_API_KEYS env var for authentication")
    app.run(host="127.0.0.1", port=5000, debug=False)
