import io

import torch
import torchvision.models as models
import torchvision.transforms as T
from fastapi import FastAPI, Request
from PIL import Image
import uvicorn

app = FastAPI()
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
_weights = models.ResNet18_Weights.IMAGENET1K_V1
model = models.resnet18(weights=_weights)
model.eval()
model.to(device)
_categories = _weights.meta["categories"]
_to_tensor = T.ToTensor()


@app.post("/classify")
async def classify(request: Request):
    body = await request.body()
    img = Image.open(io.BytesIO(body)).convert("RGB")
    x = _to_tensor(img).unsqueeze(0).to(device)
    with torch.no_grad():
        logits = model(x)
        probs = torch.softmax(logits, dim=1)
        conf, idx = probs.max(dim=1)
    return {
        "predicted_class": _categories[idx.item()],
        "confidence": float(conf.item()),
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
