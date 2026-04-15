from __future__ import annotations

import argparse
import inspect
import urllib.request
from pathlib import Path

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, Dataset
from torchvision import datasets, transforms, models
from PIL import Image


def download_checkpoint(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url) as r, open(dest, "wb") as f:
        f.write(r.read())


def load_checkpoint_from_url(url: str, cache_dir: Path) -> object:
    filename = url.rstrip("/").split("/")[-1] or "checkpoint.pt"
    path = cache_dir / filename
    if not path.is_file():
        download_checkpoint(url, path)
    load_kw = {"map_location": "cpu"}
    if "weights_only" in inspect.signature(torch.load).parameters:
        load_kw["weights_only"] = False
    return torch.load(path, **load_kw)


def get_model_ctor(arch: str):
    arch = arch.lower().replace("-", "_")
    if not hasattr(models, arch):
        raise SystemExit(f"Unknown torchvision architecture: {arch}")
    return getattr(models, arch)


def extract_state_dict(ckpt: object) -> dict:
    if isinstance(ckpt, nn.Module):
        return ckpt.state_dict()
    if isinstance(ckpt, dict):
        for key in ("state_dict", "model_state_dict", "model", "net", "module"):
            inner = ckpt.get(key)
            if isinstance(inner, dict) and inner and all(isinstance(k, str) for k in inner):
                return inner
            if isinstance(inner, nn.Module):
                return inner.state_dict()
        if ckpt and all(isinstance(k, str) for k in ckpt):
            return ckpt
    raise TypeError(f"Cannot extract state_dict from {type(ckpt)}")


def replace_head(model: nn.Module, num_classes: int) -> None:
    if hasattr(model, "fc") and isinstance(model.fc, nn.Linear):
        in_f = model.fc.in_features
        model.fc = nn.Linear(in_f, num_classes)
        return
    if hasattr(model, "classifier"):
        c = model.classifier
        if isinstance(c, nn.Sequential):
            last = c[-1]
            if isinstance(last, nn.Linear):
                in_f = last.in_features
                c[-1] = nn.Linear(in_f, num_classes)
                return
        if isinstance(c, nn.Linear):
            in_f = c.in_features
            model.classifier = nn.Linear(in_f, num_classes)
            return
    raise SystemExit("Could not replace classifier; extend replace_head() for this architecture.")


def build_model(arch: str, num_classes: int, checkpoint_url: str | None, cache_dir: Path) -> nn.Module:
    ctor = get_model_ctor(arch)
    try:
        model = ctor(weights=None)
    except TypeError:
        model = ctor(pretrained=False)
    if checkpoint_url:
        ckpt = load_checkpoint_from_url(checkpoint_url, cache_dir)
        sd = extract_state_dict(ckpt)
        missing, unexpected = model.load_state_dict(sd, strict=False)
        if missing:
            print("load_state_dict missing keys (sample):", list(missing)[:8])
        if unexpected:
            print("load_state_dict unexpected keys (sample):", list(unexpected)[:8])
    replace_head(model, num_classes)
    return model


class CsvImageDataset(Dataset):
    def __init__(self, csv_path: Path, root: Path, transform):
        self.root = Path(root)
        self.transform = transform
        self.samples: list[tuple[Path, int]] = []
        with open(csv_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = [p.strip() for p in line.split(",")]
                if len(parts) < 2:
                    continue
                rel, label_s = parts[0], parts[1]
                self.samples.append((self.root / rel, int(label_s)))

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, i: int):
        path, y = self.samples[i]
        img = Image.open(path).convert("RGB")
        if self.transform:
            img = self.transform(img)
        return img, y


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--data-root", type=Path, required=True, help="ImageFolder root or image root for CSV")
    p.add_argument("--dataset", choices=("imagefolder", "csv"), default="imagefolder")
    p.add_argument("--csv", type=Path, default=None, help="CSV lines: relative_path,label (for --dataset csv)")
    p.add_argument("--arch", type=str, default="resnet18")
    p.add_argument("--checkpoint-url", type=str, default=None)
    p.add_argument("--cache-dir", type=Path, default=Path(".checkpoints"))
    p.add_argument("--epochs", type=int, default=5)
    p.add_argument("--batch-size", type=int, default=32)
    p.add_argument("--lr", type=float, default=1e-4)
    p.add_argument("--num-workers", type=int, default=2)
    p.add_argument("--image-size", type=int, default=224)
    p.add_argument("--freeze-backbone", action="store_true")
    p.add_argument("--device", type=str, default="cuda" if torch.cuda.is_available() else "cpu")
    args = p.parse_args()

    train_tf = transforms.Compose(
        [
            transforms.RandomResizedCrop(args.image_size),
            transforms.RandomHorizontalFlip(),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ]
    )

    if args.dataset == "imagefolder":
        train_ds = datasets.ImageFolder(str(args.data_root), transform=train_tf)
        num_classes = len(train_ds.classes)
    else:
        if args.csv is None:
            raise SystemExit("--csv required when --dataset csv")
        train_ds = CsvImageDataset(args.csv, args.data_root, train_tf)
        labels = {y for _, y in train_ds.samples}
        num_classes = max(labels) + 1 if labels else 1

    train_loader = DataLoader(
        train_ds,
        batch_size=args.batch_size,
        shuffle=True,
        num_workers=args.num_workers,
        pin_memory=args.device.startswith("cuda"),
    )

    model = build_model(args.arch, num_classes, args.checkpoint_url, args.cache_dir)
    model = model.to(args.device)

    if args.freeze_backbone:
        for name, param in model.named_parameters():
            if name.startswith("fc.") or name.startswith("classifier."):
                param.requires_grad = True
            else:
                param.requires_grad = False

    params = [x for x in model.parameters() if x.requires_grad]
    optimizer = optim.AdamW(params, lr=args.lr)
    criterion = nn.CrossEntropyLoss()

    model.train()
    for epoch in range(args.epochs):
        running = 0.0
        n = 0
        for x, y in train_loader:
            x = x.to(args.device, non_blocking=True)
            y = y.to(args.device, non_blocking=True)
            optimizer.zero_grad(set_to_none=True)
            logits = model(x)
            loss = criterion(logits, y)
            loss.backward()
            optimizer.step()
            running += loss.item() * x.size(0)
            n += x.size(0)
        print(f"epoch {epoch + 1}/{args.epochs} loss {running / max(n, 1):.4f}")

    out = Path("finetuned_model.pt")
    torch.save({"arch": args.arch, "state_dict": model.state_dict(), "num_classes": num_classes}, out)
    print("saved", out)


if __name__ == "__main__":
    main()