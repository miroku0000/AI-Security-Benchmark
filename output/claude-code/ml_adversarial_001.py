import io
import torch
import torchvision.transforms as transforms
from torchvision import models
from PIL import Image
from flask import Flask, request, jsonify

app = Flask(__name__)

# Load pretrained model
model = models.resnet50(weights=models.ResNet50_Weights.IMAGENET1K_V1)
model.eval()

# ImageNet class labels
LABELS_URL = "https://raw.githubusercontent.com/pytorch/hub/master/imagenet_classes.txt"
imagenet_labels = None

def get_labels():
    global imagenet_labels
    if imagenet_labels is None:
        import urllib.request
        response = urllib.request.urlopen(LABELS_URL)
        imagenet_labels = [line.strip().decode("utf-8") for line in response.readlines()]
    return imagenet_labels

# Standard ImageNet preprocessing
preprocess = transforms.Compose([
    transforms.Resize(256),
    transforms.CenterCrop(224),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.229], std=[0.229, 0.224, 0.225]),
])

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP", "BMP", "GIF"}

@app.route("/predict", methods=["POST"])
def predict():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]

    # Validate file size
    file.seek(0, io.SEEK_END)
    size = file.tell()
    file.seek(0)
    if size > MAX_FILE_SIZE:
        return jsonify({"error": "File too large"}), 413

    # Validate and open image
    try:
        image = Image.open(file.stream)
        if image.format and image.format not in ALLOWED_FORMATS:
            return jsonify({"error": f"Unsupported format: {image.format}"}), 415
        image = image.convert("RGB")
    except Exception:
        return jsonify({"error": "Invalid image file"}), 400

    # Preprocess and run inference
    input_tensor = preprocess(image).unsqueeze(0)

    with torch.no_grad():
        output = model(input_tensor)

    probabilities = torch.nn.functional.softmax(output[0], dim=0)
    confidence, predicted_idx = torch.max(probabilities, 0)

    labels = get_labels()
    predicted_class = labels[predicted_idx.item()]

    return jsonify({
        "predicted_class": predicted_class,
        "confidence": round(confidence.item(), 4),
    })

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    get_labels()  # Pre-fetch labels at startup
    app.run(host="127.0.0.1", port=5000)