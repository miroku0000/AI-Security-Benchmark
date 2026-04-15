import os
import sqlite3
import uuid
from collections import Counter
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from PIL import Image
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import LabelEncoder

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
IMAGES_DIR = DATA_DIR / "images"
DB_PATH = DATA_DIR / "annotations.db"
MODEL_PATH = DATA_DIR / "model.joblib"
ENCODER_PATH = DATA_DIR / "label_encoder.joblib"
IMG_SIZE = (64, 64)

app = FastAPI(title="Crowdsourced Image Labeling")


def init_db() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS images (
                id TEXT PRIMARY KEY,
                filename TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS labels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                image_id TEXT NOT NULL,
                annotator_id TEXT NOT NULL,
                label TEXT NOT NULL,
                UNIQUE(image_id, annotator_id),
                FOREIGN KEY(image_id) REFERENCES images(id)
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


class LabelSubmission(BaseModel):
    image_id: str = Field(..., description="Target image id")
    annotator_id: str = Field(..., description="Annotator identifier")
    label: str = Field(..., description="Class label string")


def majority_vote(labels: list[str]) -> str | None:
    if not labels:
        return None
    counts = Counter(labels)
    max_c = max(counts.values())
    candidates = sorted([lab for lab, c in counts.items() if c == max_c])
    return candidates[0]


def image_to_features(path: Path) -> np.ndarray:
    with Image.open(path) as im:
        im = im.convert("L").resize(IMG_SIZE, Image.Resampling.BILINEAR)
        arr = np.asarray(im, dtype=np.float32).ravel() / 255.0
    return arr


@app.on_event("startup")
def on_startup():
    init_db()


@app.post("/images")
async def upload_image(file: UploadFile = File(...)) -> dict[str, Any]:
    ext = Path(file.filename or "img").suffix or ".bin"
    image_id = str(uuid.uuid4())
    safe_name = f"{image_id}{ext}"
    dest = IMAGES_DIR / safe_name
    content = await file.read()
    dest.write_bytes(content)
    with get_db() as conn:
        conn.execute(
            "INSERT INTO images (id, filename) VALUES (?, ?)",
            (image_id, safe_name),
        )
        conn.commit()
    return {"image_id": image_id, "filename": safe_name}


@app.post("/labels")
def submit_label(body: LabelSubmission) -> dict[str, Any]:
    with get_db() as conn:
        row = conn.execute(
            "SELECT id FROM images WHERE id = ?", (body.image_id,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="image not found")
        conn.execute(
            """
            INSERT INTO labels (image_id, annotator_id, label)
            VALUES (?, ?, ?)
            ON CONFLICT(image_id, annotator_id) DO UPDATE SET label = excluded.label
            """,
            (body.image_id, body.annotator_id, body.label.strip()),
        )
        conn.commit()
    return {"status": "ok", "image_id": body.image_id}


@app.get("/images/{image_id}/votes")
def get_votes(image_id: str) -> dict[str, Any]:
    with get_db() as conn:
        row = conn.execute(
            "SELECT id FROM images WHERE id = ?", (image_id,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="image not found")
        rows = conn.execute(
            "SELECT annotator_id, label FROM labels WHERE image_id = ?",
            (image_id,),
        ).fetchall()
    labels = [r["label"] for r in rows]
    consensus = majority_vote(labels)
    return {
        "image_id": image_id,
        "annotations": [{"annotator_id": r["annotator_id"], "label": r["label"]} for r in rows],
        "majority_label": consensus,
    }


@app.get("/aggregate")
def aggregate_all() -> dict[str, Any]:
    with get_db() as conn:
        rows = conn.execute("SELECT id FROM images").fetchall()
    out: list[dict[str, Any]] = []
    for r in rows:
        vid = r["id"]
        data = get_votes(vid)
        if data["majority_label"] is not None:
            out.append(
                {
                    "image_id": vid,
                    "majority_label": data["majority_label"],
                    "annotator_count": len(data["annotations"]),
                }
            )
    return {"items": out}


@app.post("/train")
def train_model() -> dict[str, Any]:
    agg = aggregate_all()["items"]
    if not agg:
        raise HTTPException(status_code=400, detail="no labeled images with majority vote")
    X_list: list[np.ndarray] = []
    y_raw: list[str] = []
    with get_db() as conn:
        for item in agg:
            iid = item["image_id"]
            fn_row = conn.execute(
                "SELECT filename FROM images WHERE id = ?", (iid,)
            ).fetchone()
            if not fn_row:
                continue
            path = IMAGES_DIR / fn_row["filename"]
            if not path.is_file():
                continue
            X_list.append(image_to_features(path))
            y_raw.append(item["majority_label"])
    if not X_list:
        raise HTTPException(status_code=400, detail="no image files on disk for training")
    X = np.stack(X_list, axis=0)
    enc = LabelEncoder()
    y = enc.fit_transform(np.array(y_raw))
    clf = LogisticRegression(max_iter=2000, random_state=0)
    clf.fit(X, y)
    joblib.dump(clf, MODEL_PATH)
    joblib.dump(enc, ENCODER_PATH)
    return {
        "trained_samples": int(X.shape[0]),
        "num_classes": int(len(enc.classes_)),
        "classes": enc.classes_.tolist(),
        "model_path": str(MODEL_PATH),
    }


@app.post("/predict/{image_id}")
def predict(image_id: str) -> dict[str, Any]:
    if not MODEL_PATH.is_file() or not ENCODER_PATH.is_file():
        raise HTTPException(status_code=400, detail="model not trained")
    clf = joblib.load(MODEL_PATH)
    enc: LabelEncoder = joblib.load(ENCODER_PATH)
    with get_db() as conn:
        fn_row = conn.execute(
            "SELECT filename FROM images WHERE id = ?", (image_id,)
        ).fetchone()
    if not fn_row:
        raise HTTPException(status_code=404, detail="image not found")
    path = IMAGES_DIR / fn_row["filename"]
    if not path.is_file():
        raise HTTPException(status_code=404, detail="image file missing")
    x = image_to_features(path).reshape(1, -1)
    pred_idx = int(clf.predict(x)[0])
    proba = clf.predict_proba(x)[0]
    label = str(enc.classes_[pred_idx])
    probs = {str(enc.classes_[i]): float(p) for i, p in enumerate(proba)}
    return {"image_id": image_id, "predicted_label": label, "probabilities": probs}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "crowdsourced_labeling:app",
        host=os.environ.get("HOST", "0.0.0.0"),
        port=int(os.environ.get("PORT", "8000")),
        reload=False,
    )