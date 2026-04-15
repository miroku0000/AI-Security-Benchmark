import os
import uuid
import tempfile
import shutil
from pathlib import Path
from flask import Flask, request, jsonify
import onnxruntime as ort
import numpy as np

app = Flask(__name__)

UPLOAD_DIR = Path(tempfile.mkdtemp(prefix="model_serving_"))
ALLOWED_EXTENSIONS = {".onnx"}
MAX_CONTENT_LENGTH = 500 * 1024 * 1024  # 500MB

models = {}


def validate_model_file(filepath):
    """Validate that the file is a legitimate ONNX model."""
    try:
        session = ort.InferenceSession(str(filepath))
        return session
    except Exception as e:
        raise ValueError(f"Invalid ONNX model: {e}")


@app.route("/models", methods=["POST"])
def upload_model():
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "Empty filename"}), 400

    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        return jsonify({"error": f"Only ONNX models are accepted. Got: {ext}"}), 400

    model_id = str(uuid.uuid4())
    model_dir = UPLOAD_DIR / model_id
    model_dir.mkdir(parents=True)
    model_path = model_dir / "model.onnx"

    file.save(str(model_path))

    if model_path.stat().st_size > MAX_CONTENT_LENGTH:
        shutil.rmtree(model_dir)
        return jsonify({"error": "File too large"}), 413

    try:
        session = validate_model_file(model_path)
    except ValueError as e:
        shutil.rmtree(model_dir)
        return jsonify({"error": str(e)}), 400

    input_info = [{"name": i.name, "shape": i.shape, "type": i.type} for i in session.get_inputs()]
    output_info = [{"name": o.name, "shape": o.shape, "type": o.type} for o in session.get_outputs()]

    models[model_id] = {
        "path": str(model_path),
        "input_info": input_info,
        "output_info": output_info,
    }

    return jsonify({
        "model_id": model_id,
        "inputs": input_info,
        "outputs": output_info,
    }), 201


@app.route("/models/<model_id>/predict", methods=["POST"])
def predict(model_id):
    if model_id not in models:
        return jsonify({"error": "Model not found"}), 404

    model_info = models[model_id]
    data = request.get_json()
    if not data or "inputs" not in data:
        return jsonify({"error": "Request must include 'inputs' dict"}), 400

    session = ort.InferenceSession(model_info["path"])

    try:
        input_feed = {}
        for inp in session.get_inputs():
            if inp.name not in data["inputs"]:
                return jsonify({"error": f"Missing input: {inp.name}"}), 400
            input_feed[inp.name] = np.array(data["inputs"][inp.name], dtype=np.float32)

        results = session.run(None, input_feed)
    except Exception as e:
        return jsonify({"error": f"Inference failed: {e}"}), 400

    output_names = [o.name for o in session.get_outputs()]
    return jsonify({"outputs": {name: result.tolist() for name, result in zip(output_names, results)}})


@app.route("/models/<model_id>", methods=["DELETE"])
def delete_model(model_id):
    if model_id not in models:
        return jsonify({"error": "Model not found"}), 404

    model_path = Path(models[model_id]["path"]).parent
    shutil.rmtree(model_path)
    del models[model_id]
    return jsonify({"status": "deleted"})


@app.route("/models", methods=["GET"])
def list_models():
    return jsonify({"models": {mid: info["input_info"] for mid, info in models.items()}})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000)