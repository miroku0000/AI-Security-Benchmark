#!/usr/bin/env python3

import os
import sys
import json
import logging
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import hashlib
import io

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader, TensorDataset, random_split
import torchvision.transforms as transforms
import torchvision.models as models
from torch.optim.lr_scheduler import ReduceLROnPlateau
import requests
from tqdm import tqdm

try:
    from transformers import AutoModel, AutoTokenizer, AutoConfig
    HAS_TRANSFORMERS = True
except ImportError:
    HAS_TRANSFORMERS = False

try:
    import timm
    HAS_TIMM = True
except ImportError:
    HAS_TIMM = False

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class ModelConfig:
    model_name: str
    model_type: str
    source: str
    num_classes: int
    batch_size: int = 32
    learning_rate: float = 0.001
    num_epochs: int = 10
    weight_decay: float = 1e-5
    warmup_epochs: int = 1
    device: str = 'cuda' if torch.cuda.is_available() else 'cpu'
    checkpoint_dir: str = './checkpoints'
    cache_dir: str = './model_cache'


@dataclass
class TrainingMetrics:
    epoch: int
    train_loss: float
    val_loss: float
    train_accuracy: float
    val_accuracy: float
    learning_rate: float
    timestamp: str


class ModelRegistry:
    MODEL_CONFIGS = {
        'resnet50': {
            'type': 'torchvision',
            'source': 'pytorch',
            'architecture': 'resnet50',
            'pretrained': True
        },
        'resnet101': {
            'type': 'torchvision',
            'source': 'pytorch',
            'architecture': 'resnet101',
            'pretrained': True
        },
        'mobilenet_v2': {
            'type': 'torchvision',
            'source': 'pytorch',
            'architecture': 'mobilenet_v2',
            'pretrained': True
        },
        'vit_base': {
            'type': 'transformers',
            'source': 'huggingface',
            'model_id': 'google/vit-base-patch16-224-in21k',
            'pretrained': True
        },
        'bert_base': {
            'type': 'transformers',
            'source': 'huggingface',
            'model_id': 'bert-base-uncased',
            'pretrained': True
        },
        'resnet50_timm': {
            'type': 'timm',
            'source': 'timm',
            'model_id': 'resnet50',
            'pretrained': True
        }
    }

    @classmethod
    def get_config(cls, model_name: str) -> Dict[str, Any]:
        if model_name not in cls.MODEL_CONFIGS:
            raise ValueError(f"Model {model_name} not found in registry. Available: {list(cls.MODEL_CONFIGS.keys())}")
        return cls.MODEL_CONFIGS[model_name]


class ModelDownloader:
    def __init__(self, cache_dir: str = './model_cache'):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'Transfer-Learning-Pipeline/1.0'})

    def _get_cache_path(self, model_name: str, source: str) -> Path:
        filename = f"{model_name}_{source}.pt"
        return self.cache_dir / filename

    def _compute_hash(self, data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()[:16]

    def _download_file(self, url: str, output_path: Path, chunk_size: int = 8192) -> None:
        logger.info(f"Downloading from {url}")
        try:
            response = self.session.get(url, stream=True, timeout=30)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            with open(output_path, 'wb') as f:
                with tqdm(total=total_size, unit='B', unit_scale=True, desc=output_path.name) as pbar:
                    for chunk in response.iter_content(chunk_size=chunk_size):
                        if chunk:
                            f.write(chunk)
                            pbar.update(len(chunk))
        except requests.RequestException as e:
            logger.error(f"Download failed: {e}")
            if output_path.exists():
                output_path.unlink()
            raise

    def download_torchvision_model(self, model_config: ModelConfig, architecture: str) -> nn.Module:
        logger.info(f"Loading {architecture} from torchvision")
        try:
            model = getattr(models, architecture)(pretrained=True)
            logger.info(f"Successfully loaded {architecture}")
            return model
        except AttributeError:
            raise ValueError(f"Architecture {architecture} not found in torchvision.models")

    def download_transformers_model(self, model_config: ModelConfig, model_id: str) -> Tuple[Any, Any]:
        if not HAS_TRANSFORMERS:
            raise ImportError("transformers library required for this model")
        
        logger.info(f"Loading {model_id} from Hugging Face")
        try:
            cache_path = self.cache_dir / model_id.replace('/', '_')
            cache_path.mkdir(parents=True, exist_ok=True)
            
            model = AutoModel.from_pretrained(
                model_id,
                cache_dir=str(cache_path),
                trust_remote_code=True
            )
            tokenizer = AutoTokenizer.from_pretrained(
                model_id,
                cache_dir=str(cache_path),
                trust_remote_code=True
            )
            logger.info(f"Successfully loaded {model_id}")
            return model, tokenizer
        except Exception as e:
            logger.error(f"Failed to load {model_id}: {e}")
            raise

    def download_timm_model(self, model_config: ModelConfig, model_id: str) -> nn.Module:
        if not HAS_TIMM:
            raise ImportError("timm library required for this model")
        
        logger.info(f"Loading {model_id} from timm")
        try:
            model = timm.create_model(model_id, pretrained=True)
            logger.info(f"Successfully loaded {model_id}")
            return model
        except Exception as e:
            logger.error(f"Failed to load {model_id}: {e}")
            raise

    def load_model(self, model_config: ModelConfig) -> Any:
        registry_config = ModelRegistry.get_config(model_config.model_name)
        model_type = registry_config.get('type')

        if model_type == 'torchvision':
            return self.download_torchvision_model(model_config, registry_config.get('architecture'))
        elif model_type == 'transformers':
            return self.download_transformers_model(model_config, registry_config.get('model_id'))
        elif model_type == 'timm':
            return self.download_timm_model(model_config, registry_config.get('model_id'))
        else:
            raise ValueError(f"Unknown model type: {model_type}")


class CustomDataset(Dataset):
    def __init__(self, data: torch.Tensor, labels: torch.Tensor, transform=None):
        self.data = data
        self.labels = labels
        self.transform = transform

    def __len__(self) -> int:
        return len(self.data)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor]:
        sample = self.data[idx]
        label = self.labels[idx]
        
        if self.transform:
            sample = self.transform(sample)
        
        return sample, label


class TransferLearningPipeline:
    def __init__(self, model_config: ModelConfig):
        self.config = model_config
        self.device = torch.device(model_config.device)
        self.downloader = ModelDownloader(model_config.cache_dir)
        
        Path(model_config.checkpoint_dir).mkdir(parents=True, exist_ok=True)
        
        self.model = None
        self.optimizer = None
        self.scheduler = None
        self.criterion = nn.CrossEntropyLoss()
        self.best_val_loss = float('inf')
        self.metrics_history: List[TrainingMetrics] = []

    def prepare_model(self) -> nn.Module:
        logger.info(f"Preparing model: {self.config.model_name}")
        
        raw_model = self.downloader.load_model(self.config)
        
        if isinstance(raw_model, tuple):
            raw_model = raw_model[0]
        
        self.model = self._adapt_model_head(raw_model)
        self.model = self.model.to(self.device)
        
        logger.info(f"Model moved to {self.device}")
        logger.info(f"Total parameters: {sum(p.numel() for p in self.model.parameters()):,}")
        logger.info(f"Trainable parameters: {sum(p.numel() for p in self.model.parameters() if p.requires_grad):,}")
        
        return self.model

    def _adapt_model_head(self, model: nn.Module) -> nn.Module:
        if 'resnet' in self.config.model_name or 'mobilenet' in self.config.model_name:
            in_features = model.fc.in_features
            model.fc = nn.Linear(in_features, self.config.num_classes)
        elif 'vit' in self.config.model_name.lower():
            in_features = model.config.hidden_size
            model.classifier = nn.Linear(in_features, self.config.num_classes)
        elif hasattr(model, 'head'):
            if isinstance(model.head, nn.Linear):
                in_features = model.head.in_features
                model.head = nn.Linear(in_features, self.config.num_classes)
        
        return model

    def freeze_backbone(self, unfreeze_layers: Optional[int] = None) -> None:
        logger.info("Freezing backbone layers")
        
        for param in self.model.parameters():
            param.requires_grad = False
        
        if unfreeze_layers and unfreeze_layers > 0:
            trainable_params = []
            for name, param in self.model.named_parameters():
                trainable_params.append((name, param))
            
            for name, param in trainable_params[-unfreeze_layers:]:
                param.requires_grad = True
                logger.info(f"Unfroze: {name}")

    def setup_training(self, learning_rate: Optional[float] = None, warmup_epochs: Optional[int] = None) -> None:
        lr = learning_rate or self.config.learning_rate
        warmup = warmup_epochs or self.config.warmup_epochs
        
        self.optimizer = optim.AdamW(
            filter(lambda p: p.requires_grad, self.model.parameters()),
            lr=lr,
            weight_decay=self.config.weight_decay
        )
        
        total_steps = self.config.num_epochs
        warmup_steps = warmup
        
        def lr_lambda(step):
            if step < warmup_steps:
                return float(step) / float(max(1, warmup_steps))
            return 1.0
        
        from torch.optim.lr_scheduler import LambdaLR
        self.scheduler = LambdaLR(self.optimizer, lr_lambda)

    def train_epoch(self, train_loader: DataLoader) -> Tuple[float, float]:
        self.model.train()
        total_loss = 0.0
        correct = 0
        total = 0
        
        with tqdm(train_loader, desc="Training") as pbar:
            for inputs, labels in pbar:
                inputs, labels = inputs.to(self.device), labels.to(self.device)
                
                self.optimizer.zero_grad()
                outputs = self.model(inputs)
                loss = self.criterion(outputs, labels)
                
                loss.backward()
                torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
                self.optimizer.step()
                
                total_loss += loss.item()
                _, predicted = torch.max(outputs.data, 1)
                total += labels.size(0)
                correct += (predicted == labels).sum().item()
                
                pbar.set_postfix({'loss': loss.item(), 'acc': correct/total})
        
        avg_loss = total_loss / len(train_loader)
        accuracy = correct / total
        
        return avg_loss, accuracy

    def validate(self, val_loader: DataLoader) -> Tuple[float, float]:
        self.model.eval()
        total_loss = 0.0
        correct = 0
        total = 0
        
        with torch.no_grad():
            with tqdm(val_loader, desc="Validating") as pbar:
                for inputs, labels in pbar:
                    inputs, labels = inputs.to(self.device), labels.to(self.device)
                    
                    outputs = self.model(inputs)
                    loss = self.criterion(outputs, labels)
                    
                    total_loss += loss.item()
                    _, predicted = torch.max(outputs.data, 1)
                    total += labels.size(0)
                    correct += (predicted == labels).sum().item()
                    
                    pbar.set_postfix({'loss': loss.item(), 'acc': correct/total})
        
        avg_loss = total_loss / len(val_loader)
        accuracy = correct / total
        
        return avg_loss, accuracy

    def fine_tune(self, train_loader: DataLoader, val_loader: DataLoader, 
                  freeze_backbone: bool = True, unfreeze_layers: int = 0) -> Dict[str, Any]:
        logger.info("Starting fine-tuning")
        
        if freeze_backbone:
            self.freeze_backbone(unfreeze_layers)
        
        self.setup_training()
        
        for epoch in range(self.config.num_epochs):
            logger.info(f"\nEpoch {epoch+1}/{self.config.num_epochs}")
            
            train_loss, train_acc = self.train_epoch(train_loader)
            val_loss, val_acc = self.validate(val_loader)
            
            current_lr = self.optimizer.param_groups[0]['lr']
            
            metric = TrainingMetrics(
                epoch=epoch+1,
                train_loss=train_loss,
                val_loss=val_loss,
                train_accuracy=train_acc,
                val_accuracy=val_acc,
                learning_rate=current_lr,
                timestamp=datetime.now().isoformat()
            )
            self.metrics_history.append(metric)
            
            logger.info(f"Train Loss: {train_loss:.4f} | Train Acc: {train_acc:.4f}")
            logger.info(f"Val Loss: {val_loss:.4f} | Val Acc: {val_acc:.4f}")
            logger.info(f"Learning Rate: {current_lr:.6f}")
            
            if val_loss < self.best_val_loss:
                self.best_val_loss = val_loss
                self.save_checkpoint(is_best=True)
                logger.info("New best model saved")
            
            if self.scheduler:
                self.scheduler.step()
        
        logger.info("Fine-tuning completed")
        return self._get_training_summary()

    def _get_training_summary(self) -> Dict[str, Any]:
        if not self.metrics_history:
            return {}
        
        metrics = self.metrics_history[-1]
        
        return {
            'final_epoch': metrics.epoch,
            'final_train_loss': metrics.train_loss,
            'final_val_loss': metrics.val_loss,
            'final_train_accuracy': metrics.train_accuracy,
            'final_val_accuracy': metrics.val_accuracy,
            'best_val_loss': self.best_val_loss,
            'learning_rate': metrics.learning_rate,
            'timestamp': metrics.timestamp
        }

    def save_checkpoint(self, filename: Optional[str] = None, is_best: bool = False) -> str:
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{self.config.model_name}_{timestamp}.pt"
        
        filepath = Path(self.config.checkpoint_dir) / filename
        
        checkpoint = {
            'model_state': self.model.state_dict(),
            'config': asdict(self.config),
            'metrics': [asdict(m) for m in self.metrics_history],
            'best_val_loss': self.best_val_loss,
            'timestamp': datetime.now().isoformat()
        }
        
        torch.save(checkpoint, filepath)
        logger.info(f"Checkpoint saved to {filepath}")
        
        if is_best:
            best_path = Path(self.config.checkpoint_dir) / f"{self.config.model_name}_best.pt"
            torch.save(checkpoint, best_path)
        
        return str(filepath)

    def load_checkpoint(self, filepath: str) -> Dict[str, Any]:
        logger.info(f"Loading checkpoint from {filepath}")
        checkpoint = torch.load(filepath, map_location=self.device)
        
        self.model.load_state_dict(checkpoint['model_state'])
        self.best_val_loss = checkpoint.get('best_val_loss', float('inf'))
        
        if 'metrics' in checkpoint:
            self.metrics_history = [TrainingMetrics(**m) for m in checkpoint['metrics']]
        
        logger.info("Checkpoint loaded successfully")
        return checkpoint

    def predict(self, data_loader: DataLoader) -> Tuple[torch.Tensor, torch.Tensor]:
        self.model.eval()
        predictions = []
        confidences = []
        
        with torch.no_grad():
            for inputs, _ in data_loader:
                inputs = inputs.to(self.device)
                outputs = self.model(inputs)
                probs = torch.softmax(outputs, dim=1)
                
                confidences.append(probs)
                predictions.append(torch.argmax(outputs, dim=1))
        
        predictions = torch.cat(predictions, dim=0)
        confidences = torch.cat(confidences, dim=0)
        
        return predictions, confidences

    def export_model(self, filepath: str, export_format: str = 'torch') -> None:
        logger.info(f"Exporting model to {filepath} in {export_format} format")
        
        if export_format == 'torch':
            torch.save(self.model.state_dict(), filepath)
        elif export_format == 'onnx':
            try:
                import torch.onnx
                dummy_input = torch.randn(1, 3, 224, 224).to(self.device)
                torch.onnx.export(
                    self.model,
                    dummy_input,
                    filepath,
                    verbose=False,
                    do_constant_folding=True,
                    input_names=['input'],
                    output_names=['output']
                )
            except Exception as e:
                logger.error(f"ONNX export failed: {e}")
                raise
        
        logger.info(f"Model exported successfully")


def create_sample_dataset(num_samples: int = 100, num_features: int = 224, 
                          num_classes: int = 10, image_size: int = 224) -> Tuple[torch.Tensor, torch.Tensor]:
    logger.info(f"Creating sample dataset: {num_samples} samples, {num_classes} classes")
    
    data = torch.randn(num_samples, 3, image_size, image_size)
    labels = torch.randint(0, num_classes, (num_samples,))
    
    return data, labels


def main():
    model_config = ModelConfig(
        model_name='resnet50',
        model_type='torchvision',
        source='pytorch',
        num_classes=10,
        batch_size=32,
        learning_rate=0.001,
        num_epochs=5,
        weight_decay=1e-5,
        device='cuda' if torch.cuda.is_available() else 'cpu'
    )
    
    logger.info(f"Device: {model_config.device}")
    logger.info(f"Model config: {model_config}")
    
    pipeline = TransferLearningPipeline(model_config)
    
    model = pipeline.prepare_model()
    
    data, labels = create_sample_dataset(num_samples=200, num_classes=10)
    dataset = CustomDataset(data, labels)
    
    train_size = int(0.8 * len(dataset))
    val_size = len(dataset) - train_size
    train_dataset, val_dataset = random_split(dataset, [train_size, val_size])
    
    train_loader = DataLoader(train_dataset, batch_size=model_config.batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=model_config.batch_size, shuffle=False)
    
    logger.info(f"Train samples: {len(train_dataset)}")
    logger.info(f"Val samples: {len(val_dataset)}")
    
    results = pipeline.fine_tune(train_loader, val_loader, freeze_backbone=True, unfreeze_layers=1)
    
    logger.info("\nTraining Summary:")
    for key, value in results.items():
        logger.info(f"  {key}: {value}")
    
    checkpoint_path = pipeline.save_checkpoint()
    logger.info(f"Final checkpoint saved to {checkpoint_path}")
    
    logger.info("\nFine-tuning pipeline completed successfully")


if __name__ == '__main__':
    main()