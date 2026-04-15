The script is at `transfer_learning_pipeline.py`. Key security decisions:

- **`torch.load(..., weights_only=True)`** — blocks arbitrary code execution via pickle deserialization, which is the main risk with loading model files from the internet
- **URL validation** — only allows HTTPS from a trusted host allowlist
- **SHA-256 checksum verification** — optional but supported for integrity checks
- **Prefers `torchvision` built-in weights** — avoids pickle entirely when possible
- **Saves only `state_dict`** — not full model objects, keeping saved files safer to reload