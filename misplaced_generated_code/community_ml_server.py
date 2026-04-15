import io
import json
import os
import shutil
import sqlite3
import threading
import time
import uuid
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from PIL import Image

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
import tensorflow as tf  # noqa: E402


APP_NAME = os.environ.get("COMMUNITY_ML_APP_NAME", "community-ml")
HOST = os.environ.get("HOST", "127.0.0.1")
PORT = int(os.environ.get("PORT", "8000"))

DATA_DIR = Path(os.environ.get("COMMUNITY_ML_DATA_DIR", "./community_ml_data")).expanduser().resolve()
DB_PATH = Path(os.environ.get("COMMUNITY_ML_DB_PATH", str(DATA_DIR / "contrib.db"))).expanduser().resolve()
STORAGE_DIR = Path(os.environ.get("COMMUNITY_ML_STORAGE_DIR", str(DATA_DIR / "storage"))).expanduser().resolve()
MODELS_DIR = Path(os.environ.get("COMMUNITY_ML_MODELS_DIR", str(DATA_DIR / "models"))).expanduser().resolve()
MAX_UPLOAD_BYTES = int(os.environ.get("COMMUNITY_ML_MAX_UPLOAD_BYTES", str(50 * 1024 * 1024)))
MAX_IMAGE_PIXELS = int(os.environ.get("COMMUNITY_ML_MAX_IMAGE_PIXELS", str(20_000_000)))
MAX_IMAGES_PER_UPLOAD = int(os.environ.get("COMMUNITY_ML_MAX_IMAGES_PER_UPLOAD", "5000"))

DEFAULT_IMAGE_SIZE = int(os.environ.get("COMMUNITY_ML_IMAGE_SIZE", "224"))
DEFAULT_BATCH_SIZE = int(os.environ.get("COMMUNITY_ML_BATCH_SIZE", "32"))
DEFAULT_EPOCHS = int(os.environ.get("COMMUNITY_ML_EPOCHS", "5"))
DEFAULT_VALIDATION_SPLIT = float(os.environ.get("COMMUNITY_ML_VALIDATION_SPLIT", "0.15"))

_train_lock = threading.Lock()
_predict_lock = threading.Lock()


@dataclass(frozen=True)
class ModelArtifacts:
    model_path: Path
    label_map_path: Path

    @property
    def exists(self) -> bool:
        return self.model_path.is_file() and self.label_map_path.is_file()


def _now() -> int:
    return int(time.time())


def _ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    MODELS_DIR.mkdir(parents=True, exist_ok=True)


def _db_connect() -> sqlite3.Connection:
    _ensure_dirs()
    conn = sqlite3.connect(str(DB_PATH), timeout=30, isolation_level=None, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def _db_init() -> None:
    conn = _db_connect()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS examples (
                id TEXT PRIMARY KEY,
                dataset_id TEXT NOT NULL,
                contributor TEXT,
                label TEXT NOT NULL,
                original_filename TEXT,
                stored_path TEXT NOT NULL,
                sha256 TEXT NOT NULL,
                width INTEGER NOT NULL,
                height INTEGER NOT NULL,
                created_at INTEGER NOT NULL
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_examples_label ON examples(label)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_examples_created_at ON examples(created_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_examples_dataset ON examples(dataset_id)")
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_examples_sha_label ON examples(sha256, label)")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS trainings (
                id TEXT PRIMARY KEY,
                created_at INTEGER NOT NULL,
                num_examples INTEGER NOT NULL,
                num_labels INTEGER NOT NULL,
                image_size INTEGER NOT NULL,
                batch_size INTEGER NOT NULL,
                epochs INTEGER NOT NULL,
                val_split REAL NOT NULL,
                metrics_json TEXT NOT NULL
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_trainings_created_at ON trainings(created_at)")
    finally:
        conn.close()


def _sha256_bytes(data: bytes) -> str:
    import hashlib

    h = hashlib.sha256()
    h.update(data)
    return h.hexdigest()


def _safe_filename(name: str) -> str:
    name = (name or "").strip().replace("\\", "/")
    name = name.split("/")[-1]
    name = "".join(ch for ch in name if ch.isalnum() or ch in ("-", "_", ".", " "))
    name = name.strip().replace(" ", "_")
    if not name:
        return "file"
    if len(name) > 200:
        root, dot, ext = name.rpartition(".")
        ext = (dot + ext) if dot else ""
        name = (root[: 200 - len(ext)] + ext) if ext else name[:200]
    return name


def _read_limited(upload: UploadFile, max_bytes: int) -> bytes:
    data = upload.file.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise HTTPException(status_code=413, detail="upload_too_large")
    return data


def _open_image_validate(image_bytes: bytes) -> Tuple[Image.Image, int, int, str]:
    if not image_bytes:
        raise HTTPException(status_code=400, detail="empty_image")
    sha = _sha256_bytes(image_bytes)
    try:
        Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS
        with Image.open(io.BytesIO(image_bytes)) as im:
            im.load()
            w, h = int(im.width), int(im.height)
            if w <= 0 or h <= 0:
                raise HTTPException(status_code=400, detail="invalid_image_dimensions")
            mode = im.mode
            im2 = im.convert("RGB") if mode != "RGB" else im.copy()
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=400, detail="invalid_image")
    return im2, w, h, sha


def _store_image_bytes(dataset_id: str, original_filename: str, image_bytes: bytes) -> Tuple[Path, int, int, str]:
    im, w, h, sha = _open_image_validate(image_bytes)
    ds_dir = (STORAGE_DIR / "datasets" / dataset_id).resolve()
    ds_dir.mkdir(parents=True, exist_ok=True)
    safe = _safe_filename(original_filename)
    ext = (Path(safe).suffix or ".jpg").lower()
    if ext not in (".jpg", ".jpeg", ".png", ".webp"):
        ext = ".jpg"
    stored_name = f"{uuid.uuid4().hex}{ext}"
    stored_path = (ds_dir / stored_name).resolve()
    if os.path.commonpath([str(ds_dir), str(stored_path)]) != str(ds_dir):
        raise HTTPException(status_code=400, detail="invalid_storage_path")
    try:
        if ext in (".png", ".webp"):
            im.save(stored_path, format=ext.lstrip(".").upper())
        else:
            im.save(stored_path, format="JPEG", quality=92, optimize=True)
    except Exception:
        raise HTTPException(status_code=500, detail="failed_to_store_image")
    return stored_path, w, h, sha


def _parse_csv_mapping(csv_bytes: bytes) -> List[Tuple[str, str]]:
    import csv

    if not csv_bytes:
        raise HTTPException(status_code=400, detail="empty_csv")
    text = csv_bytes.decode("utf-8-sig", errors="replace")
    f = io.StringIO(text)
    try:
        reader = csv.DictReader(f)
    except Exception:
        raise HTTPException(status_code=400, detail="invalid_csv")
    if not reader.fieldnames:
        raise HTTPException(status_code=400, detail="invalid_csv_headers")
    fields = {h.strip().lower(): h for h in reader.fieldnames if isinstance(h, str)}
    if "filename" not in fields or "label" not in fields:
        raise HTTPException(status_code=400, detail="csv_requires_filename_and_label_columns")
    fn_key = fields["filename"]
    lb_key = fields["label"]
    out: List[Tuple[str, str]] = []
    for row in reader:
        if not isinstance(row, dict):
            continue
        fn = (row.get(fn_key) or "").strip()
        lb = (row.get(lb_key) or "").strip()
        if not fn or not lb:
            continue
        out.append((fn.replace("\\", "/").split("/")[-1], lb))
        if len(out) > MAX_IMAGES_PER_UPLOAD:
            raise HTTPException(status_code=400, detail="too_many_rows")
    if not out:
        raise HTTPException(status_code=400, detail="no_valid_rows")
    return out


def _extract_zip_images(zip_bytes: bytes) -> Dict[str, bytes]:
    if not zip_bytes:
        raise HTTPException(status_code=400, detail="empty_zip")
    out: Dict[str, bytes] = {}
    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            infos = [i for i in zf.infolist() if not i.is_dir()]
            if len(infos) > MAX_IMAGES_PER_UPLOAD:
                raise HTTPException(status_code=400, detail="too_many_files_in_zip")
            for info in infos:
                name = (info.filename or "").replace("\\", "/").split("/")[-1]
                name = _safe_filename(name)
                if not name:
                    continue
                if info.file_size > MAX_UPLOAD_BYTES:
                    raise HTTPException(status_code=413, detail="file_in_zip_too_large")
                data = zf.read(info)
                if len(data) > MAX_UPLOAD_BYTES:
                    raise HTTPException(status_code=413, detail="file_in_zip_too_large")
                if name not in out:
                    out[name] = data
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=400, detail="invalid_zip")
    if not out:
        raise HTTPException(status_code=400, detail="no_files_in_zip")
    return out


def _insert_examples(
    *,
    dataset_id: str,
    contributor: Optional[str],
    items: Sequence[Tuple[str, str, bytes]],
) -> Dict[str, Any]:
    if not items:
        raise HTTPException(status_code=400, detail="no_examples")
    if len(items) > MAX_IMAGES_PER_UPLOAD:
        raise HTTPException(status_code=400, detail="too_many_images")

    conn = _db_connect()
    created = 0
    skipped_duplicates = 0
    stored: List[Dict[str, Any]] = []
    try:
        for original_filename, label, image_bytes in items:
            stored_path, w, h, sha = _store_image_bytes(dataset_id, original_filename, image_bytes)
            ex_id = uuid.uuid4().hex
            try:
                conn.execute(
                    """
                    INSERT INTO examples(id, dataset_id, contributor, label, original_filename, stored_path, sha256, width, height, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        ex_id,
                        dataset_id,
                        contributor,
                        label,
                        original_filename,
                        str(stored_path),
                        sha,
                        int(w),
                        int(h),
                        _now(),
                    ),
                )
                created += 1
                stored.append(
                    {
                        "id": ex_id,
                        "label": label,
                        "stored_path": str(stored_path),
                        "sha256": sha,
                        "width": int(w),
                        "height": int(h),
                    }
                )
            except sqlite3.IntegrityError:
                skipped_duplicates += 1
                try:
                    stored_path.unlink(missing_ok=True)
                except Exception:
                    pass
    finally:
        conn.close()
    return {
        "dataset_id": dataset_id,
        "created": created,
        "skipped_duplicates": skipped_duplicates,
        "total_received": len(items),
        "stored": stored[:50],
    }


def _all_examples() -> List[sqlite3.Row]:
    conn = _db_connect()
    try:
        rows = conn.execute(
            """
            SELECT id, label, stored_path
            FROM examples
            ORDER BY created_at ASC
            """
        ).fetchall()
        return list(rows)
    finally:
        conn.close()


def _labels_summary() -> Dict[str, int]:
    conn = _db_connect()
    try:
        rows = conn.execute("SELECT label, COUNT(*) AS c FROM examples GROUP BY label ORDER BY c DESC").fetchall()
        return {str(r["label"]): int(r["c"]) for r in rows}
    finally:
        conn.close()


def _latest_artifacts() -> ModelArtifacts:
    return ModelArtifacts(model_path=(MODELS_DIR / "latest" / "model.keras"), label_map_path=(MODELS_DIR / "latest" / "labels.json"))


def _save_artifacts(*, model: tf.keras.Model, labels: List[str], metrics: Dict[str, Any]) -> None:
    target_dir = (MODELS_DIR / "latest").resolve()
    tmp_dir = (MODELS_DIR / f".tmp-{uuid.uuid4().hex}").resolve()
    tmp_dir.mkdir(parents=True, exist_ok=True)
    try:
        model.save(str(tmp_dir / "model.keras"))
        (tmp_dir / "labels.json").write_text(json.dumps({"labels": labels}, indent=2, ensure_ascii=False), encoding="utf-8")
        (tmp_dir / "metrics.json").write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")
        target_dir.parent.mkdir(parents=True, exist_ok=True)
        if target_dir.exists():
            shutil.rmtree(target_dir)
        tmp_dir.rename(target_dir)
    finally:
        if tmp_dir.exists():
            try:
                shutil.rmtree(tmp_dir)
            except Exception:
                pass


def _build_dataset(
    paths: Sequence[str],
    labels_idx: Sequence[int],
    *,
    image_size: int,
    batch_size: int,
    training: bool,
) -> tf.data.Dataset:
    x = tf.convert_to_tensor(list(paths), dtype=tf.string)
    y = tf.convert_to_tensor(list(labels_idx), dtype=tf.int32)
    ds = tf.data.Dataset.from_tensor_slices((x, y))

    def _load(path: tf.Tensor, label: tf.Tensor) -> Tuple[tf.Tensor, tf.Tensor]:
        img_bytes = tf.io.read_file(path)
        img = tf.io.decode_image(img_bytes, channels=3, expand_animations=False)
        img = tf.image.resize(img, [image_size, image_size], method=tf.image.ResizeMethod.BILINEAR)
        img = tf.cast(img, tf.float32) / 255.0
        return img, label

    ds = ds.map(_load, num_parallel_calls=tf.data.AUTOTUNE)
    if training:
        ds = ds.shuffle(min(10_000, len(paths)), reshuffle_each_iteration=True)
    ds = ds.batch(batch_size, drop_remainder=False).prefetch(tf.data.AUTOTUNE)
    return ds


def _build_model(num_classes: int, image_size: int) -> tf.keras.Model:
    inputs = tf.keras.Input(shape=(image_size, image_size, 3))
    x = tf.keras.layers.RandomFlip("horizontal")(inputs)
    x = tf.keras.layers.RandomRotation(0.05)(x)
    x = tf.keras.layers.RandomZoom(0.1)(x)

    x = tf.keras.layers.Conv2D(32, 3, padding="same", activation="relu")(x)
    x = tf.keras.layers.MaxPool2D()(x)
    x = tf.keras.layers.Conv2D(64, 3, padding="same", activation="relu")(x)
    x = tf.keras.layers.MaxPool2D()(x)
    x = tf.keras.layers.Conv2D(128, 3, padding="same", activation="relu")(x)
    x = tf.keras.layers.MaxPool2D()(x)
    x = tf.keras.layers.SeparableConv2D(256, 3, padding="same", activation="relu")(x)
    x = tf.keras.layers.GlobalAveragePooling2D()(x)
    x = tf.keras.layers.Dropout(0.25)(x)
    outputs = tf.keras.layers.Dense(num_classes, activation="softmax")(x)

    model = tf.keras.Model(inputs=inputs, outputs=outputs)
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=1e-3),
        loss=tf.keras.losses.SparseCategoricalCrossentropy(),
        metrics=[tf.keras.metrics.SparseCategoricalAccuracy(name="accuracy")],
    )
    return model


_cached_model: Optional[tf.keras.Model] = None
_cached_labels: Optional[List[str]] = None
_cached_mtime: Optional[float] = None


def _load_latest_for_predict() -> Tuple[tf.keras.Model, List[str]]:
    global _cached_model, _cached_labels, _cached_mtime
    arts = _latest_artifacts()
    if not arts.exists:
        raise HTTPException(status_code=404, detail="model_not_trained")
    model_mtime = max(arts.model_path.stat().st_mtime, arts.label_map_path.stat().st_mtime)
    with _predict_lock:
        if _cached_model is not None and _cached_labels is not None and _cached_mtime == model_mtime:
            return _cached_model, _cached_labels
        labels_obj = json.loads(arts.label_map_path.read_text(encoding="utf-8"))
        labels = labels_obj.get("labels")
        if not isinstance(labels, list) or not all(isinstance(x, str) for x in labels) or not labels:
            raise HTTPException(status_code=500, detail="invalid_label_map")
        model = tf.keras.models.load_model(str(arts.model_path))
        _cached_model = model
        _cached_labels = labels
        _cached_mtime = model_mtime
        return model, labels


app = FastAPI(title=APP_NAME)


@app.on_event("startup")
def _startup() -> None:
    _db_init()
    _ensure_dirs()


@app.get("/health")
def health() -> Dict[str, Any]:
    arts = _latest_artifacts()
    return {
        "ok": True,
        "app": APP_NAME,
        "time": _now(),
        "data_dir": str(DATA_DIR),
        "num_examples": sum(_labels_summary().values()),
        "labels": _labels_summary(),
        "model_trained": bool(arts.exists),
    }


@app.get("/stats")
def stats() -> Dict[str, Any]:
    conn = _db_connect()
    try:
        ex_count = int(conn.execute("SELECT COUNT(*) AS c FROM examples").fetchone()["c"])
        label_count = int(conn.execute("SELECT COUNT(DISTINCT label) AS c FROM examples").fetchone()["c"])
        train_row = conn.execute("SELECT * FROM trainings ORDER BY created_at DESC LIMIT 1").fetchone()
        last_training = dict(train_row) if train_row is not None else None
    finally:
        conn.close()
    return {
        "num_examples": ex_count,
        "num_labels": label_count,
        "labels": _labels_summary(),
        "latest_training": last_training,
    }


@app.post("/upload_example")
async def upload_example(
    image: UploadFile = File(...),
    label: str = Form(...),
    contributor: Optional[str] = Form(None),
    dataset_id: Optional[str] = Form(None),
) -> JSONResponse:
    label = (label or "").strip()
    if not label:
        raise HTTPException(status_code=400, detail="label_required")
    dataset_id = (dataset_id or uuid.uuid4().hex).strip()
    contributor = (contributor or "").strip() or None
    img_bytes = _read_limited(image, MAX_UPLOAD_BYTES)
    res = _insert_examples(dataset_id=dataset_id, contributor=contributor, items=[(image.filename or "image", label, img_bytes)])
    return JSONResponse(res)


@app.post("/upload_dataset")
async def upload_dataset(
    csv_file: UploadFile = File(...),
    images: Optional[List[UploadFile]] = File(None),
    images_zip: Optional[UploadFile] = File(None),
    contributor: Optional[str] = Form(None),
    dataset_id: Optional[str] = Form(None),
) -> JSONResponse:
    dataset_id = (dataset_id or uuid.uuid4().hex).strip()
    contributor = (contributor or "").strip() or None

    csv_bytes = _read_limited(csv_file, MAX_UPLOAD_BYTES)
    mapping = _parse_csv_mapping(csv_bytes)
    required = {fn for fn, _ in mapping}

    payload_images: Dict[str, bytes] = {}
    if images_zip is not None:
        zbytes = _read_limited(images_zip, MAX_UPLOAD_BYTES)
        payload_images.update(_extract_zip_images(zbytes))

    if images:
        if len(images) > MAX_IMAGES_PER_UPLOAD:
            raise HTTPException(status_code=400, detail="too_many_images")
        for up in images:
            name = _safe_filename(up.filename or "image")
            payload_images.setdefault(name, _read_limited(up, MAX_UPLOAD_BYTES))

    if not payload_images:
        raise HTTPException(status_code=400, detail="no_images_provided")

    items: List[Tuple[str, str, bytes]] = []
    missing = []
    for fn, lb in mapping:
        b = payload_images.get(_safe_filename(fn))
        if b is None:
            b = payload_images.get(fn)
        if b is None:
            missing.append(fn)
            continue
        items.append((fn, lb, b))

    if missing:
        raise HTTPException(status_code=400, detail={"error": "missing_images_for_csv_rows", "missing": missing[:200], "missing_count": len(missing)})
    if len(items) > MAX_IMAGES_PER_UPLOAD:
        raise HTTPException(status_code=400, detail="too_many_examples")

    res = _insert_examples(dataset_id=dataset_id, contributor=contributor, items=items)
    res["unique_filenames_in_csv"] = len(required)
    res["uploaded_files"] = len(payload_images)
    return JSONResponse(res)


@app.post("/train")
def train(
    epochs: int = Form(DEFAULT_EPOCHS),
    batch_size: int = Form(DEFAULT_BATCH_SIZE),
    image_size: int = Form(DEFAULT_IMAGE_SIZE),
    validation_split: float = Form(DEFAULT_VALIDATION_SPLIT),
    min_per_label: int = Form(1),
    seed: int = Form(1337),
) -> JSONResponse:
    epochs = int(max(1, min(int(epochs), 200)))
    batch_size = int(max(1, min(int(batch_size), 512)))
    image_size = int(max(32, min(int(image_size), 512)))
    validation_split = float(max(0.05, min(float(validation_split), 0.5)))
    min_per_label = int(max(1, min(int(min_per_label), 10_000)))
    seed = int(seed)

    if not _train_lock.acquire(blocking=False):
        raise HTTPException(status_code=409, detail="training_in_progress")
    try:
        rows = _all_examples()
        if not rows:
            raise HTTPException(status_code=400, detail="no_training_data")

        by_label: Dict[str, List[str]] = {}
        for r in rows:
            label = str(r["label"])
            path = str(r["stored_path"])
            if not os.path.isfile(path):
                continue
            by_label.setdefault(label, []).append(path)

        by_label = {k: v for k, v in by_label.items() if len(v) >= min_per_label}
        if len(by_label) < 2:
            raise HTTPException(status_code=400, detail="need_at_least_two_labels_with_enough_examples")

        labels = sorted(by_label.keys())
        label_to_idx = {lb: i for i, lb in enumerate(labels)}

        paths: List[str] = []
        y: List[int] = []
        for lb in labels:
            for p in by_label[lb]:
                paths.append(p)
                y.append(label_to_idx[lb])

        n = len(paths)
        if n < 10:
            raise HTTPException(status_code=400, detail="not_enough_examples")

        rng = np.random.default_rng(seed)
        idx = np.arange(n)
        rng.shuffle(idx)
        paths = [paths[i] for i in idx]
        y = [y[i] for i in idx]

        n_val = max(1, int(round(n * validation_split)))
        n_train = n - n_val
        if n_train < 1 or n_val < 1:
            raise HTTPException(status_code=400, detail="invalid_train_val_split")

        train_ds = _build_dataset(paths[:n_train], y[:n_train], image_size=image_size, batch_size=batch_size, training=True)
        val_ds = _build_dataset(paths[n_train:], y[n_train:], image_size=image_size, batch_size=batch_size, training=False)

        model = _build_model(num_classes=len(labels), image_size=image_size)
        cb = [
            tf.keras.callbacks.EarlyStopping(monitor="val_accuracy", patience=3, restore_best_weights=True),
            tf.keras.callbacks.ReduceLROnPlateau(monitor="val_loss", factor=0.5, patience=2, min_lr=1e-6),
        ]
        history = model.fit(train_ds, validation_data=val_ds, epochs=epochs, callbacks=cb, verbose=1)
        eval_res = model.evaluate(val_ds, verbose=0)

        metrics = {
            "trained_at": _now(),
            "num_examples": n,
            "num_train": n_train,
            "num_val": n_val,
            "labels": labels,
            "image_size": image_size,
            "batch_size": batch_size,
            "epochs_requested": epochs,
            "history": {k: [float(x) for x in v] for k, v in (history.history or {}).items()},
            "val_eval": {"loss": float(eval_res[0]), "accuracy": float(eval_res[1])} if isinstance(eval_res, (list, tuple)) and len(eval_res) >= 2 else eval_res,
        }

        _save_artifacts(model=model, labels=labels, metrics=metrics)

        conn = _db_connect()
        try:
            tr_id = uuid.uuid4().hex
            conn.execute(
                """
                INSERT INTO trainings(id, created_at, num_examples, num_labels, image_size, batch_size, epochs, val_split, metrics_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    tr_id,
                    metrics["trained_at"],
                    int(n),
                    int(len(labels)),
                    int(image_size),
                    int(batch_size),
                    int(epochs),
                    float(validation_split),
                    json.dumps(metrics, ensure_ascii=False),
                ),
            )
        finally:
            conn.close()

        global _cached_model, _cached_labels, _cached_mtime
        with _predict_lock:
            _cached_model = None
            _cached_labels = None
            _cached_mtime = None

        return JSONResponse({"ok": True, "training_id": tr_id, "metrics": metrics})
    finally:
        _train_lock.release()


@app.post("/predict")
async def predict(image: UploadFile = File(...)) -> JSONResponse:
    img_bytes = _read_limited(image, MAX_UPLOAD_BYTES)
    im, _, _, _ = _open_image_validate(img_bytes)
    model, labels = _load_latest_for_predict()
    arts = _latest_artifacts()
    metrics_path = arts.model_path.parent / "metrics.json"
    try:
        metrics = json.loads(metrics_path.read_text(encoding="utf-8")) if metrics_path.is_file() else {}
        image_size = int(metrics.get("image_size", DEFAULT_IMAGE_SIZE))
        image_size = int(max(32, min(image_size, 512)))
    except Exception:
        image_size = DEFAULT_IMAGE_SIZE

    im = im.resize((image_size, image_size))
    arr = (np.asarray(im).astype(np.float32) / 255.0)[None, ...]
    preds = model.predict(arr, verbose=0)
    if not isinstance(preds, np.ndarray):
        preds = np.asarray(preds)
    if preds.ndim != 2 or preds.shape[0] != 1 or preds.shape[1] != len(labels):
        raise HTTPException(status_code=500, detail="invalid_model_output")
    probs = preds[0].astype(float)
    topk = int(min(10, len(labels)))
    idx = np.argsort(-probs)[:topk]
    out = [{"label": labels[int(i)], "prob": float(probs[int(i)])} for i in idx]
    return JSONResponse({"ok": True, "filename": image.filename, "top": out, "predicted": out[0]["label"], "prob": out[0]["prob"]})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=HOST, port=PORT)
