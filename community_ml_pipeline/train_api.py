import io
import json
import threading
import uuid
import zipfile
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np
import pandas as pd
import tensorflow as tf
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from PIL import Image
from tensorflow import keras

BASE = Path(__file__).resolve().parent
DATA = BASE / "data"
UPLOADS = DATA / "uploads"
IMAGES = DATA / "images"
MODEL_DIR = DATA / "model"
MANIFEST = DATA / "manifest.json"
COMMUNITY_CSV = DATA / "community_labels.csv"
IMG_SIZE = (224, 224)
BATCH = 16
EPOCHS = 5

_lock = threading.Lock()
_training = False
_app_state = {"last_train": None, "num_classes": 0, "labels": []}


def _ensure_dirs():
    for p in (DATA, UPLOADS, IMAGES, MODEL_DIR):
        p.mkdir(parents=True, exist_ok=True)


def _load_manifest():
    if MANIFEST.exists():
        with open(MANIFEST, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"class_names": [], "version": 0}


def _save_manifest(m):
    with open(MANIFEST, "w", encoding="utf-8") as f:
        json.dump(m, f, indent=2)


def _normalize_df(df: pd.DataFrame) -> pd.DataFrame:
    cols = {c.lower().strip(): c for c in df.columns}
    path_key = None
    label_key = None
    for k in ("filepath", "path", "image", "filename", "file"):
        if k in cols:
            path_key = cols[k]
            break
    for k in ("label", "class", "category", "target"):
        if k in cols:
            label_key = cols[k]
            break
    if not path_key or not label_key:
        raise ValueError("CSV needs columns for image path and label")
    out = pd.DataFrame(
        {"filepath": df[path_key].astype(str), "label": df[label_key].astype(str)}
    )
    out = out.dropna()
    return out


def _append_community(rows: pd.DataFrame):
    _ensure_dirs()
    if COMMUNITY_CSV.exists():
        old = pd.read_csv(COMMUNITY_CSV)
        combined = pd.concat([old, rows], ignore_index=True)
    else:
        combined = rows
    combined.to_csv(COMMUNITY_CSV, index=False)


def _collect_training_frame() -> pd.DataFrame:
    _ensure_dirs()
    frames = []
    for csv_path in UPLOADS.glob("*.csv"):
        try:
            df = pd.read_csv(csv_path)
            frames.append(_normalize_df(df))
        except Exception:
            continue
    if COMMUNITY_CSV.exists():
        try:
            df = pd.read_csv(COMMUNITY_CSV)
            frames.append(_normalize_df(df))
        except Exception:
            pass
    if not frames:
        raise ValueError("No valid CSV data")
    full = pd.concat(frames, ignore_index=True)
    full["filepath"] = full["filepath"].apply(lambda p: str(Path(p).as_posix()))
    return full


def _resolve_image_path(raw: str) -> Optional[Path]:
    p = Path(raw)
    if p.is_file():
        return p.resolve()
    cand = (IMAGES / raw).resolve()
    if cand.is_file():
        return cand
    cand = (IMAGES / Path(raw).name).resolve()
    if cand.is_file():
        return cand
    cand = (UPLOADS / raw).resolve()
    if cand.is_file():
        return cand
    return None


def _collect_paths_labels(df: pd.DataFrame, class_names: List[str]) -> Tuple[List[str], List[int]]:
    paths: List[str] = []
    labels: List[int] = []
    for _, row in df.iterrows():
        rp = _resolve_image_path(row["filepath"])
        if rp is None:
            continue
        lab = row["label"]
        if lab not in class_names:
            continue
        paths.append(str(rp))
        labels.append(class_names.index(lab))
    return paths, labels


def _make_tf_dataset(paths: List[str], labels: List[int]) -> tf.data.Dataset:
    label_ds = tf.data.Dataset.from_tensor_slices(labels)
    path_ds = tf.data.Dataset.from_tensor_slices(paths)

    def load_decode(path, label):
        img_bytes = tf.io.read_file(path)
        img = tf.io.decode_image(img_bytes, channels=3, expand_animations=False)
        img = tf.image.resize(img, IMG_SIZE)
        img = tf.cast(img, tf.float32) / 255.0
        return img, label

    ds = tf.data.Dataset.zip((path_ds, label_ds))
    return ds.map(load_decode, num_parallel_calls=tf.data.AUTOTUNE)


def _make_model(num_classes: int) -> keras.Model:
    base = keras.applications.MobileNetV2(
        input_shape=(*IMG_SIZE, 3),
        include_top=False,
        weights="imagenet",
    )
    base.trainable = False
    inputs = keras.Input(shape=(*IMG_SIZE, 3))
    x = base(inputs, training=False)
    x = keras.layers.GlobalAveragePooling2D()(x)
    x = keras.layers.Dropout(0.2)(x)
    outputs = keras.layers.Dense(num_classes, activation="softmax")(x)
    model = keras.Model(inputs, outputs)
    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=1e-3),
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )
    return model


def _run_train():
    global _training
    with _lock:
        if _training:
            return {"ok": False, "error": "training_in_progress"}
        _training = True
    try:
        df = _collect_training_frame()
        labels_sorted = sorted(df["label"].unique().tolist())
        n = len(labels_sorted)
        if n < 2:
            raise ValueError("Need at least 2 classes")
        manifest = _load_manifest()
        prev_n = len(manifest.get("class_names", []))
        paths, y = _collect_paths_labels(df, labels_sorted)
        cnt = len(paths)
        if cnt < 2:
            raise ValueError("Resolved image count too low")
        idx = np.arange(cnt)
        rng = np.random.default_rng(42)
        rng.shuffle(idx)
        paths = [paths[i] for i in idx]
        y = [y[i] for i in idx]
        val_size = max(1, int(cnt * 0.15))
        vpaths, vy = paths[:val_size], y[:val_size]
        tpaths, ty = paths[val_size:], y[val_size:]
        if not tpaths:
            tpaths, ty = paths, y
            vpaths, vy = paths[:1], y[:1]
        train_ds = _make_tf_dataset(tpaths, ty).batch(BATCH).prefetch(tf.data.AUTOTUNE)
        val_ds = _make_tf_dataset(vpaths, vy).batch(BATCH).prefetch(tf.data.AUTOTUNE)
        model_path = MODEL_DIR / "classifier.keras"
        if model_path.exists() and prev_n == n:
            try:
                model = keras.models.load_model(model_path)
                if model.output_shape[-1] != n:
                    model = _make_model(n)
            except Exception:
                model = _make_model(n)
        else:
            model = _make_model(n)
        hist = model.fit(train_ds, validation_data=val_ds, epochs=EPOCHS, verbose=0)
        model.save(model_path)
        manifest["class_names"] = labels_sorted
        manifest["version"] = manifest.get("version", 0) + 1
        _save_manifest(manifest)
        _app_state["last_train"] = {
            "version": manifest["version"],
            "classes": n,
            "samples": cnt,
            "final_acc": float(hist.history["accuracy"][-1]),
            "val_acc": float(hist.history.get("val_accuracy", [0])[-1]),
        }
        _app_state["num_classes"] = n
        _app_state["labels"] = labels_sorted
        return {"ok": True, "result": _app_state["last_train"]}
    except Exception as e:
        return {"ok": False, "error": str(e)}
    finally:
        with _lock:
            _training = False


_ensure_dirs()
app = FastAPI(title="CommunityImageTrainer")


@app.get("/health")
def health():
    return {"status": "ok", "training": _training, "manifest": _load_manifest()}


@app.post("/upload/dataset")
async def upload_dataset(
    csv_file: UploadFile = File(...),
    images_archive: Optional[UploadFile] = File(None),
):
    _ensure_dirs()
    uid = uuid.uuid4().hex[:12]
    dest_csv = UPLOADS / f"dataset_{uid}.csv"
    content = await csv_file.read()
    dest_csv.write_bytes(content)
    if images_archive and images_archive.filename:
        raw = await images_archive.read()
        zpath = UPLOADS / f"images_{uid}.zip"
        zpath.write_bytes(raw)
        with zipfile.ZipFile(io.BytesIO(raw), "r") as zf:
            zf.extractall(IMAGES)
    return {"saved_csv": dest_csv.name, "images_extracted": bool(images_archive)}


@app.post("/upload/images")
async def upload_images(files: List[UploadFile] = File(...)):
    _ensure_dirs()
    saved = []
    for uf in files:
        if not uf.filename:
            continue
        safe = Path(uf.filename).name
        target = IMAGES / safe
        target.write_bytes(await uf.read())
        saved.append(safe)
    return {"saved": saved}


@app.post("/contribute")
async def contribute(
    image: UploadFile = File(...),
    label: str = Form(...),
):
    _ensure_dirs()
    if not image.filename:
        raise HTTPException(400, "missing file")
    ext = Path(image.filename).suffix.lower() or ".jpg"
    if ext not in (".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"):
        ext = ".jpg"
    fname = f"c_{uuid.uuid4().hex}{ext}"
    dest = IMAGES / fname
    dest.write_bytes(await image.read())
    row = pd.DataFrame({"filepath": [fname], "label": [label.strip()]})
    _append_community(row)
    return {"filepath": fname, "label": label.strip()}


@app.post("/train")
def train():
    res = _run_train()
    if not res.get("ok"):
        raise HTTPException(400, res.get("error", "train_failed"))
    return res


@app.post("/predict")
async def predict(image: UploadFile = File(...)):
    model_path = MODEL_DIR / "classifier.keras"
    if not model_path.exists():
        raise HTTPException(400, "model_not_trained")
    manifest = _load_manifest()
    class_names = manifest.get("class_names") or []
    if not class_names:
        raise HTTPException(400, "no_class_manifest")
    model = keras.models.load_model(model_path)
    raw = await image.read()
    im = Image.open(io.BytesIO(raw)).convert("RGB")
    im = im.resize(IMG_SIZE)
    arr = np.asarray(im, dtype=np.float32) / 255.0
    batch = np.expand_dims(arr, 0)
    probs = model.predict(batch, verbose=0)[0]
    idx = int(np.argmax(probs))
    return {
        "label": class_names[idx],
        "confidence": float(probs[idx]),
        "all": {class_names[i]: float(probs[i]) for i in range(len(class_names))},
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8765)
