import io
import pickle
import uuid
from typing import Any, Dict, Optional

from fastapi import FastAPI, File, Header, HTTPException, UploadFile
from pydantic import BaseModel

app = FastAPI(title="Multi-tenant Model Serving")

_tenant_models: Dict[str, Dict[str, Any]] = {}


def _get_tenant_models(tenant_id: str) -> Dict[str, Any]:
    if tenant_id not in _tenant_models:
        _tenant_models[tenant_id] = {}
    return _tenant_models[tenant_id]


def _require_tenant(header_tenant: Optional[str], path_tenant: str) -> str:
    if header_tenant and header_tenant != path_tenant:
        raise HTTPException(status_code=403, detail="tenant mismatch")
    return path_tenant


class PredictRequest(BaseModel):
    data: Any


@app.post("/tenants/{tenant_id}/models")
async def upload_model(
    tenant_id: str,
    file: UploadFile = File(...),
    x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-Id"),
):
    tid = _require_tenant(x_tenant_id, tenant_id)
    raw = await file.read()
    try:
        obj = pickle.load(io.BytesIO(raw))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"invalid pickle: {e}") from e
    model_id = str(uuid.uuid4())
    _get_tenant_models(tid)[model_id] = obj
    return {"model_id": model_id, "tenant_id": tid}


@app.post("/tenants/{tenant_id}/models/{model_id}/predict")
async def predict(
    tenant_id: str,
    model_id: str,
    body: PredictRequest,
    x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-Id"),
):
    tid = _require_tenant(x_tenant_id, tenant_id)
    models = _get_tenant_models(tid)
    if model_id not in models:
        raise HTTPException(status_code=404, detail="model not found")
    model = models[model_id]
    try:
        if hasattr(model, "predict"):
            out = model.predict(body.data)
        elif callable(model):
            out = model(body.data)
        else:
            raise HTTPException(
                status_code=400,
                detail="model has no predict() and is not callable",
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"inference failed: {e}") from e
    return {"prediction": _serialize_output(out)}


def _serialize_output(out: Any) -> Any:
    try:
        return out.tolist()
    except Exception:
        pass
    if isinstance(out, (list, dict, str, int, float, bool, type(None))):
        return out
    return str(out)


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=8000)
