#!/usr/bin/env python3
# pip install fastapi uvicorn face_recognition scikit-learn numpy pillow pydantic
import io
import os
import pickle
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import face_recognition
import numpy as np
from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel
from sklearn.dummy import DummyClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.svm import SVC
import uvicorn

DEFAULT_DATA_DIR = Path(os.environ.get("EMPLOYEE_PHOTOS_DIR", "employee_photos"))
MODEL_PATH = Path(os.environ.get("FACE_MODEL_PATH", "face_model.pkl"))
ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}

_lock = threading.Lock()
_app_state: Dict[str, Any] = {
    "clf": None,
    "label_encoder": None,
    "class_names": [],
    "trained": False,
}


class DistributionResponse(BaseModel):
    face_detected: bool
    num_faces: int
    training_classes: List[str]
    probabilities: Dict[str, float]
    predicted_class: Optional[str]
    raw_decision_function: Optional[List[float]] = None


def _iter_employee_images(root: Path) -> List[Tuple[str, Path]]:
    pairs: List[Tuple[str, Path]] = []
    if not root.is_dir():
        return pairs
    for person_dir in sorted(root.iterdir()):
        if not person_dir.is_dir():
            continue
        name = person_dir.name
        for p in sorted(person_dir.rglob("*")):
            if p.suffix.lower() in ALLOWED_EXT and p.is_file():
                pairs.append((name, p))
    return pairs


def _load_image_as_rgb(data: bytes) -> np.ndarray:
    return face_recognition.load_image_file(io.BytesIO(data))


def _encodings_from_image(rgb: np.ndarray) -> List[np.ndarray]:
    return [np.array(e, dtype=np.float64) for e in face_recognition.face_encodings(rgb)]


def train_from_directory(data_dir: Path) -> None:
    pairs = _iter_employee_images(data_dir)
    if not pairs:
        raise ValueError(f"No images found under {data_dir} (expected subfolders per employee).")

    X_list: List[np.ndarray] = []
    y_list: List[str] = []
    for label, path in pairs:
        rgb = face_recognition.load_image_file(str(path))
        encs = _encodings_from_image(rgb)
        for enc in encs:
            X_list.append(enc)
            y_list.append(label)

    if not X_list:
        raise ValueError("No face encodings extracted from training images.")

    X = np.vstack(X_list)
    le = LabelEncoder()
    y = le.fit_transform(np.array(y_list))

    if len(le.classes_) == 1:
        clf = DummyClassifier(strategy="constant", constant=0)
        clf.fit(X, y)
    else:
        clf = SVC(kernel="rbf", C=1.0, gamma="scale", probability=True, class_weight="balanced")
        clf.fit(X, y)

    with _lock:
        _app_state["clf"] = clf
        _app_state["label_encoder"] = le
        _app_state["class_names"] = list(le.classes_)
        _app_state["trained"] = True

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(MODEL_PATH, "wb") as f:
        pickle.dump({"clf": clf, "label_encoder": le}, f)


def load_model_if_exists() -> bool:
    if not MODEL_PATH.is_file():
        return False
    with open(MODEL_PATH, "rb") as f:
        blob = pickle.load(f)
    with _lock:
        _app_state["clf"] = blob["clf"]
        _app_state["label_encoder"] = blob["label_encoder"]
        _app_state["class_names"] = list(blob["label_encoder"].classes_)
        _app_state["trained"] = True
    return True


def _probability_distribution(encoding: np.ndarray) -> Tuple[Dict[str, float], Optional[str], Optional[List[float]]]:
    with _lock:
        clf = _app_state["clf"]
        le: Optional[LabelEncoder] = _app_state["label_encoder"]
        class_names: List[str] = _app_state["class_names"]

    if clf is None or not class_names:
        raise RuntimeError("Model not trained.")

    X = encoding.reshape(1, -1)
    proba = clf.predict_proba(X)[0]
    cls_arr = np.asarray(clf.classes_)
    if le is not None and cls_arr.dtype != object:
        dist = {
            str(le.inverse_transform([int(cls_arr[j])])[0]): float(proba[j])
            for j in range(len(proba))
        }
        j_best = int(np.argmax(proba))
        pred_class = str(le.inverse_transform([int(cls_arr[j_best])])[0])
    else:
        names = [str(x) for x in cls_arr]
        dist = {names[i]: float(proba[i]) for i in range(len(proba))}
        j_best = int(np.argmax(proba))
        pred_class = names[j_best] if names else None
    try:
        raw_df = clf.decision_function(X)[0]
        df_out = [float(x) for x in np.asarray(raw_df).ravel()]
    except Exception:
        df_out = None
    return dist, pred_class, df_out


app = FastAPI(title="Office Face Identification")


@app.on_event("startup")
def _startup() -> None:
    data_dir = DEFAULT_DATA_DIR
    if data_dir.is_dir() and any(data_dir.iterdir()):
        try:
            train_from_directory(data_dir)
            return
        except ValueError:
            pass
    load_model_if_exists()


@app.get("/health")
def health() -> Dict[str, Any]:
    with _lock:
        trained = bool(_app_state["trained"])
        n_classes = len(_app_state["class_names"])
    return {"status": "ok", "trained": trained, "num_classes": n_classes}


@app.post("/train", response_model=Dict[str, Any])
def train_endpoint(data_dir: Optional[str] = None) -> Dict[str, Any]:
    root = Path(data_dir) if data_dir else DEFAULT_DATA_DIR
    train_from_directory(root)
    with _lock:
        names = list(_app_state["class_names"])
    return {"ok": True, "classes": names, "model_path": str(MODEL_PATH)}


@app.post("/identify", response_model=DistributionResponse)
async def identify(file: UploadFile = File(...)) -> DistributionResponse:
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Empty file.")

    rgb = _load_image_as_rgb(raw)
    encodings = _encodings_from_image(rgb)
    n = len(encodings)

    with _lock:
        class_names = list(_app_state["class_names"])
        trained = bool(_app_state["trained"])

    if not trained:
        raise HTTPException(status_code=503, detail="Model not trained. POST /train first.")

    if n == 0:
        return DistributionResponse(
            face_detected=False,
            num_faces=0,
            training_classes=class_names,
            probabilities={c: 0.0 for c in class_names},
            predicted_class=None,
            raw_decision_function=None,
        )

    enc = encodings[0]
    dist, pred, df = _probability_distribution(enc)
    full = {c: float(dist.get(c, 0.0)) for c in class_names}
    ordered = {k: full[k] for k in sorted(full.keys(), key=lambda x: -full[x])}

    return DistributionResponse(
        face_detected=True,
        num_faces=n,
        training_classes=class_names,
        probabilities=ordered,
        predicted_class=pred,
        raw_decision_function=df,
    )


@app.post("/identify_all_faces")
async def identify_all_faces(file: UploadFile = File(...)) -> Dict[str, Any]:
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Empty file.")

    with _lock:
        class_names = list(_app_state["class_names"])
        trained = bool(_app_state["trained"])

    if not trained:
        raise HTTPException(status_code=503, detail="Model not trained.")

    rgb = _load_image_as_rgb(raw)
    encodings = _encodings_from_image(rgb)
    faces_out: List[Dict[str, Any]] = []
    for i, enc in enumerate(encodings):
        dist, pred, df = _probability_distribution(enc)
        full = {c: float(dist.get(c, 0.0)) for c in class_names}
        ordered = {k: full[k] for k in sorted(full.keys(), key=lambda x: -full[x])}
        faces_out.append(
            {
                "face_index": i,
                "predicted_class": pred,
                "probabilities": ordered,
                "raw_decision_function": df,
            }
        )
    return {
        "num_faces": len(encodings),
        "training_classes": class_names,
        "faces": faces_out,
    }


if __name__ == "__main__":
    uvicorn.run("facial_recognition_api:app", host="0.0.0.0", port=int(os.environ.get("PORT", "8000")), reload=False)
