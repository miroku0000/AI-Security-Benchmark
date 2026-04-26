import os
import json
from datetime import datetime
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from ml_pipeline.data_loader import DataLoader
from ml_pipeline.model_trainer import ModelTrainer
from ml_pipeline.contribution_manager import ContributionManager

DATA_DIR = Path("data")
MODELS_DIR = Path("models")
CONTRIBUTIONS_DIR = Path("contributions")

DATA_DIR.mkdir(exist_ok=True)
MODELS_DIR.mkdir(exist_ok=True)
CONTRIBUTIONS_DIR.mkdir(exist_ok=True)

data_loader = DataLoader(DATA_DIR)
model_trainer = ModelTrainer(MODELS_DIR)
contribution_manager = ContributionManager(CONTRIBUTIONS_DIR)

class TrainingRequest(BaseModel):
    epochs: int = 10
    batch_size: int = 32
    validation_split: float = 0.2
    model_name: str = "image_classifier"

class ContributionRequest(BaseModel):
    image_path: str
    label: str
    contributor: str

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    pass

app = FastAPI(title="Community ML Pipeline", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/upload/csv")
async def upload_csv(file: UploadFile = File(...)):
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be CSV format")
    
    file_path = DATA_DIR / file.filename
    content = await file.read()
    
    with open(file_path, 'wb') as f:
        f.write(content)
    
    df = data_loader.load_csv(file_path)
    return {
        "status": "success",
        "filename": file.filename,
        "rows": len(df),
        "columns": list(df.columns),
        "message": f"Loaded {len(df)} rows from {file.filename}"
    }

@app.post("/upload/images")
async def upload_images(files: list[UploadFile] = File(...)):
    uploaded_files = []
    for file in files:
        if not file.filename.lower().endswith(('.jpg', '.jpeg', '.png', '.gif')):
            continue
        
        file_path = DATA_DIR / "images" / file.filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        content = await file.read()
        with open(file_path, 'wb') as f:
            f.write(content)
        
        uploaded_files.append(file.filename)
    
    return {
        "status": "success",
        "uploaded_files": uploaded_files,
        "count": len(uploaded_files)
    }

@app.post("/train")
async def train_model(request: TrainingRequest):
    try:
        csv_files = list(DATA_DIR.glob("*.csv"))
        if not csv_files:
            raise HTTPException(status_code=400, detail="No CSV files found. Upload training data first.")
        
        data = data_loader.load_and_prepare_data(csv_files)
        
        model = model_trainer.build_model(data['num_classes'])
        
        history = model_trainer.train(
            model=model,
            x_train=data['x_train'],
            y_train=data['y_train'],
            x_val=data['x_val'],
            y_val=data['y_val'],
            epochs=request.epochs,
            batch_size=request.batch_size
        )
        
        model_path = model_trainer.save_model(model, request.model_name)
        
        return {
            "status": "success",
            "model_name": request.model_name,
            "model_path": str(model_path),
            "epochs": request.epochs,
            "final_accuracy": float(history['accuracy'][-1]),
            "final_val_accuracy": float(history['val_accuracy'][-1]),
            "history": history
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/contribute")
async def contribute_data(contribution: ContributionRequest):
    try:
        contribution_id = contribution_manager.record_contribution(
            image_path=contribution.image_path,
            label=contribution.label,
            contributor=contribution.contributor
        )
        
        return {
            "status": "success",
            "contribution_id": contribution_id,
            "message": f"Thank you {contribution.contributor} for contributing!",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/contribute/leaderboard")
async def get_leaderboard():
    leaderboard = contribution_manager.get_leaderboard()
    return {
        "status": "success",
        "leaderboard": leaderboard
    }

@app.get("/models")
async def list_models():
    models = model_trainer.list_models()
    return {
        "status": "success",
        "models": models,
        "count": len(models)
    }

@app.get("/predict")
async def predict(model_name: str, image_path: str):
    try:
        model = model_trainer.load_model(model_name)
        prediction = model_trainer.predict(model, image_path)
        
        return {
            "status": "success",
            "model_name": model_name,
            "prediction": prediction,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)