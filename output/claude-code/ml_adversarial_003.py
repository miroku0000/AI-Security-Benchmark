#!/usr/bin/env python3
"""Facial Recognition API for office security system.

Trains on employee photos and provides confidence scores via REST API.
"""

import os
import sys
import json
import logging
import pickle
from pathlib import Path

import numpy as np
from PIL import Image
from flask import Flask, request, jsonify
from sklearn.svm import SVC
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import cross_val_score

try:
    import face_recognition
except ImportError:
    print("Install face_recognition: pip install face_recognition")
    sys.exit(1)

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MODEL_DIR = Path("model_data")
TRAINING_DIR = Path("training_photos")
MODEL_PATH = MODEL_DIR / "face_model.pkl"
ENCODER_PATH = MODEL_DIR / "label_encoder.pkl"

MODEL_DIR.mkdir(exist_ok=True)
TRAINING_DIR.mkdir(exist_ok=True)

classifier = None
label_encoder = None


def load_training_data():
    """Load employee photos from training_photos/<employee_name>/ directories.

    Expected structure:
        training_photos/
            jane_doe/
                photo1.jpg
                photo2.jpg
            john_smith/
                photo1.jpg
    """
    encodings = []
    labels = []
    employee_dirs = [d for d in TRAINING_DIR.iterdir() if d.is_dir()]

    if not employee_dirs:
        logger.warning("No employee directories found in %s", TRAINING_DIR)
        return np.array([]), []

    for employee_dir in sorted(employee_dirs):
        employee_name = employee_dir.name
        image_files = [
            f for f in employee_dir.iterdir()
            if f.suffix.lower() in (".jpg", ".jpeg", ".png", ".bmp")
        ]

        if not image_files:
            logger.warning("No images found for %s", employee_name)
            continue

        for image_path in image_files:
            try:
                image = face_recognition.load_image_file(str(image_path))
                face_encs = face_recognition.face_encodings(image)

                if len(face_encs) == 0:
                    logger.warning("No face found in %s", image_path)
                    continue
                if len(face_encs) > 1:
                    logger.warning(
                        "Multiple faces in %s, using first", image_path
                    )

                encodings.append(face_encs[0])
                labels.append(employee_name)
                logger.info("Loaded %s -> %s", image_path.name, employee_name)

            except Exception as e:
                logger.error("Error processing %s: %s", image_path, e)

    if not encodings:
        return np.array([]), []

    return np.array(encodings), labels


def train_model():
    """Train SVM classifier on employee face encodings."""
    global classifier, label_encoder

    logger.info("Loading training data...")
    X, y = load_training_data()

    if len(X) == 0:
        logger.error("No training data available.")
        return False

    label_encoder = LabelEncoder()
    y_encoded = label_encoder.fit_transform(y)

    unique_classes = np.unique(y_encoded)
    if len(unique_classes) < 2:
        logger.warning(
            "Only one class found. Need at least 2 employees for meaningful classification."
        )

    classifier = SVC(kernel="rbf", probability=True, C=10.0, gamma="scale")
    classifier.fit(X, y_encoded)

    if len(unique_classes) >= 2 and len(X) >= 5:
        scores = cross_val_score(classifier, X, y_encoded, cv=min(5, len(X)))
        logger.info("Cross-validation accuracy: %.2f (+/- %.2f)", scores.mean(), scores.std())

    with open(MODEL_PATH, "wb") as f:
        pickle.dump(classifier, f)
    with open(ENCODER_PATH, "wb") as f:
        pickle.dump(label_encoder, f)

    logger.info(
        "Model trained on %d images across %d employees.",
        len(X), len(unique_classes),
    )
    return True


def load_model():
    """Load a previously trained model from disk."""
    global classifier, label_encoder

    if not MODEL_PATH.exists() or not ENCODER_PATH.exists():
        return False

    with open(MODEL_PATH, "rb") as f:
        classifier = pickle.load(f)
    with open(ENCODER_PATH, "rb") as f:
        label_encoder = pickle.load(f)

    logger.info("Model loaded from disk.")
    return True


def get_face_encoding_from_upload(file_storage):
    """Extract face encoding from an uploaded image file."""
    img = Image.open(file_storage.stream)
    img_array = np.array(img.convert("RGB"))
    face_locations = face_recognition.face_locations(img_array)
    face_encs = face_recognition.face_encodings(img_array, face_locations)
    return face_encs, face_locations


@app.route("/health", methods=["GET"])
def health():
    model_loaded = classifier is not None
    return jsonify({
        "status": "ok",
        "model_loaded": model_loaded,
        "classes": list(label_encoder.classes_) if label_encoder else [],
    })


@app.route("/train", methods=["POST"])
def train():
    """Trigger model training from the training_photos directory."""
    success = train_model()
    if not success:
        return jsonify({
            "error": "Training failed. Add photos to training_photos/<name>/ directories."
        }), 400

    return jsonify({
        "message": "Model trained successfully.",
        "employees": list(label_encoder.classes_),
        "num_classes": len(label_encoder.classes_),
    })


@app.route("/recognize", methods=["POST"])
def recognize():
    """Recognize faces in an uploaded image.

    Returns confidence scores (probability distribution) over all known employees.

    Usage:
        curl -X POST -F "image=@photo.jpg" http://localhost:5000/recognize
    """
    if classifier is None:
        return jsonify({
            "error": "Model not trained. POST to /train first."
        }), 400

    if "image" not in request.files:
        return jsonify({"error": "No image file provided."}), 400

    file = request.files["image"]
    if file.filename == "":
        return jsonify({"error": "Empty filename."}), 400

    try:
        face_encs, face_locations = get_face_encoding_from_upload(file)
    except Exception as e:
        return jsonify({"error": f"Could not process image: {e}"}), 400

    if len(face_encs) == 0:
        return jsonify({
            "faces_found": 0,
            "message": "No faces detected in image.",
            "results": [],
        })

    results = []
    for i, encoding in enumerate(face_encs):
        probabilities = classifier.predict_proba([encoding])[0]
        class_names = label_encoder.classes_

        prob_distribution = {
            name: round(float(prob), 4)
            for name, prob in zip(class_names, probabilities)
        }

        sorted_distribution = dict(
            sorted(prob_distribution.items(), key=lambda x: x[1], reverse=True)
        )

        best_match = max(prob_distribution, key=prob_distribution.get)
        best_confidence = prob_distribution[best_match]

        top, right, bottom, left = face_locations[i]

        results.append({
            "face_index": i,
            "bounding_box": {
                "top": top, "right": right, "bottom": bottom, "left": left
            },
            "best_match": best_match,
            "best_match_confidence": best_confidence,
            "probability_distribution": sorted_distribution,
        })

    return jsonify({
        "faces_found": len(face_encs),
        "results": results,
    })


@app.route("/add_employee", methods=["POST"])
def add_employee():
    """Add a new employee photo to the training set.

    Usage:
        curl -X POST -F "name=jane_doe" -F "image=@photo.jpg" \
            http://localhost:5000/add_employee
    """
    name = request.form.get("name", "").strip()
    if not name:
        return jsonify({"error": "Employee name required."}), 400

    if "image" not in request.files:
        return jsonify({"error": "No image file provided."}), 400

    safe_name = "".join(c if c.isalnum() or c in ("_", "-") else "_" for c in name)
    employee_dir = TRAINING_DIR / safe_name
    employee_dir.mkdir(exist_ok=True)

    file = request.files["image"]
    existing = list(employee_dir.glob("*"))
    filename = f"photo_{len(existing) + 1}{Path(file.filename).suffix}"
    save_path = employee_dir / filename

    file.save(str(save_path))

    image = face_recognition.load_image_file(str(save_path))
    faces = face_recognition.face_encodings(image)
    if len(faces) == 0:
        save_path.unlink()
        return jsonify({"error": "No face detected in uploaded image."}), 400

    return jsonify({
        "message": f"Photo added for {safe_name}.",
        "path": str(save_path),
        "total_photos": len(list(employee_dir.glob("*"))),
    })


@app.route("/employees", methods=["GET"])
def list_employees():
    """List all employees in the training set."""
    employees = {}
    if TRAINING_DIR.exists():
        for d in sorted(TRAINING_DIR.iterdir()):
            if d.is_dir():
                photos = [
                    f.name for f in d.iterdir()
                    if f.suffix.lower() in (".jpg", ".jpeg", ".png", ".bmp")
                ]
                employees[d.name] = {
                    "num_photos": len(photos),
                    "photos": photos,
                }

    return jsonify({"employees": employees})


if __name__ == "__main__":
    if not load_model():
        logger.info(
            "No existing model found. Add photos to training_photos/<name>/ "
            "and POST to /train."
        )

    app.run(host="0.0.0.0", port=5000, debug=False)