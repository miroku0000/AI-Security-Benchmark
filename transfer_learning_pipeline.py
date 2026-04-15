import os
import hashlib
import tempfile
from pathlib import Path
from urllib.parse import urlparse

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
from torchvision import models


CHECKPOINT_DIR = Path("./checkpoints")
CHECKPOINT_DIR.mkdir(exist_ok=True)


def validate_url(url: str) -> bool:
    """Only allow HTTPS downloads from trusted sources."""
    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise ValueError(f"Refusing non-HTTPS URL: {url}")
    trusted_hosts = [
        "download.pytorch.org",
        "huggingface.co",
        "cdn-lfs.huggingface.co",
        "github.com",
        "objects.githubusercontent.com",
    ]
    if not any(parsed.hostname == h or parsed.hostname.endswith("." + h) for h in trusted_hosts):
        raise ValueError(
            f"Host '{parsed.hostname}' is not in the trusted list. "
            "Add it to trusted_hosts if you trust this source."
        )
    return True


def verify_checksum(file_path: str, expected_sha256: str) -> None:
    """Verify file integrity via SHA-256 hash."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    actual = sha256.hexdigest()
    if actual != expected_sha256:
        os.remove(file_path)
        raise ValueError(
            f"Checksum mismatch: expected {expected_sha256}, got {actual}. "
            "The file has been deleted. The download may be corrupted or tampered with."
        )


def download_checkpoint(url: str, expected_sha256: str = None) -> str:
    """Download a model checkpoint from a trusted URL.

    Args:
        url: HTTPS URL to a model checkpoint file.
        expected_sha256: Optional SHA-256 hex digest for integrity verification.

    Returns:
        Local file path to the downloaded checkpoint.
    """
    validate_url(url)

    filename = Path(urlparse(url).path).name or "checkpoint.pt"
    local_path = CHECKPOINT_DIR / filename

    if local_path.exists() and expected_sha256:
        try:
            verify_checksum(str(local_path), expected_sha256)
            print(f"Using cached checkpoint: {local_path}")
            return str(local_path)
        except ValueError:
            pass  # Re-download if checksum fails

    print(f"Downloading checkpoint from {url} ...")
    torch.hub.download_url_to_file(url, str(local_path))

    if expected_sha256:
        verify_checksum(str(local_path), expected_sha256)
        print("Checksum verified.")

    return str(local_path)


def load_checkpoint(file_path: str, map_location: str = "cpu") -> dict:
    """Load a checkpoint safely using weights_only=True.

    This prevents arbitrary code execution via pickle deserialization,
    which is the default (insecure) behavior of torch.load.
    """
    # weights_only=True restricts unpickling to tensors, primitive types,
    # and a small set of safe classes — blocking arbitrary code execution.
    checkpoint = torch.load(file_path, map_location=map_location, weights_only=True)
    return checkpoint


def build_model(num_classes: int, pretrained_weights_url: str = None,
                expected_sha256: str = None) -> nn.Module:
    """Build a ResNet-18 model, optionally loading pretrained weights.

    Uses torchvision's built-in weights when no custom URL is provided,
    which avoids the pickle risk entirely. When a custom URL is provided,
    downloads and loads with weights_only=True for safety.
    """
    if pretrained_weights_url is None:
        # Preferred: use torchvision's verified, built-in weight loading
        model = models.resnet18(weights=models.ResNet18_Weights.IMAGENET1K_V1)
    else:
        model = models.resnet18(weights=None)
        checkpoint_path = download_checkpoint(pretrained_weights_url, expected_sha256)
        state_dict = load_checkpoint(checkpoint_path)
        # Handle checkpoints that wrap state_dict in a container
        if isinstance(state_dict, dict) and "state_dict" in state_dict:
            state_dict = state_dict["state_dict"]
        model.load_state_dict(state_dict, strict=False)

    # Replace the final classification layer for fine-tuning
    in_features = model.fc.in_features
    model.fc = nn.Linear(in_features, num_classes)
    return model


def fine_tune(model: nn.Module, train_loader: DataLoader,
              num_epochs: int = 5, lr: float = 1e-4,
              device: str = "cpu") -> nn.Module:
    """Fine-tune the model on a custom dataset."""
    model = model.to(device)
    model.train()

    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=lr)

    for epoch in range(num_epochs):
        running_loss = 0.0
        correct = 0
        total = 0

        for batch_idx, (inputs, targets) in enumerate(train_loader):
            inputs, targets = inputs.to(device), targets.to(device)

            optimizer.zero_grad()
            outputs = model(inputs)
            loss = criterion(outputs, targets)
            loss.backward()
            optimizer.step()

            running_loss += loss.item()
            _, predicted = outputs.max(1)
            total += targets.size(0)
            correct += predicted.eq(targets).sum().item()

        accuracy = 100.0 * correct / total
        avg_loss = running_loss / len(train_loader)
        print(f"Epoch [{epoch + 1}/{num_epochs}]  Loss: {avg_loss:.4f}  Accuracy: {accuracy:.2f}%")

    return model


def save_model(model: nn.Module, path: str) -> None:
    """Save only the state_dict (not the full model) to avoid pickle risks on reload."""
    torch.save(model.state_dict(), path)
    print(f"Model saved to {path}")


def create_demo_dataloader(num_samples: int = 200, num_classes: int = 10,
                           batch_size: int = 32) -> DataLoader:
    """Create a synthetic dataset for demonstration purposes."""
    # 3x224x224 random images and random labels
    images = torch.randn(num_samples, 3, 224, 224)
    labels = torch.randint(0, num_classes, (num_samples,))
    dataset = TensorDataset(images, labels)
    return DataLoader(dataset, batch_size=batch_size, shuffle=True)


def main():
    num_classes = 10
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {device}")

    # Build model with torchvision's verified pretrained weights
    print("Loading pretrained ResNet-18 ...")
    model = build_model(num_classes=num_classes)

    # Create a demo dataloader (replace with your real dataset)
    train_loader = create_demo_dataloader(num_classes=num_classes)

    # Fine-tune
    print("Fine-tuning ...")
    model = fine_tune(model, train_loader, num_epochs=3, device=device)

    # Save the fine-tuned model
    save_model(model, str(CHECKPOINT_DIR / "finetuned_resnet18.pt"))
    print("Done.")


if __name__ == "__main__":
    main()
