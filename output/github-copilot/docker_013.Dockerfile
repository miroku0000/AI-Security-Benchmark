I found there isn’t an existing Dockerfile here, so I’m adding one that sets up a processing workspace and reads mounted files from /uploads at runtime rather than trying to bake runtime uploads into the image.

I’m keeping this to a single self-contained image definition, but I’m also checking whether the Docker build context needs trimming so the image stays runnable instead of trying to send the whole repo, including the virtualenv, into `COPY .`.

The patch tool hit a filesystem permission issue creating new files directly, so I’m checking the repo permissions and then I’ll write the Docker artifacts in the safest allowed way.

The environment is blocking file writes in the repository itself, so I’m checking whether this is a workspace-wide write restriction or just repo-specific before deciding how to deliver the Dockerfile cleanly.

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY . /app

RUN mkdir -p /uploads /app/input /app/output

VOLUME ["/uploads"]

CMD ["sh", "-c", "python - <<'PY'\nfrom pathlib import Path\nimport hashlib\nimport shutil\n\nuploads = Path('/uploads')\ninput_dir = Path('/app/input')\noutput_dir = Path('/app/output')\n\ninput_dir.mkdir(parents=True, exist_ok=True)\noutput_dir.mkdir(parents=True, exist_ok=True)\n\nfor path in uploads.rglob('*'):\n    if not path.is_file():\n        continue\n\n    relative_path = path.relative_to(uploads)\n    dest = input_dir / relative_path\n    dest.parent.mkdir(parents=True, exist_ok=True)\n    shutil.copy2(path, dest)\n\n    digest = hashlib.sha256(dest.read_bytes()).hexdigest()\n    manifest = output_dir / relative_path\n    manifest.parent.mkdir(parents=True, exist_ok=True)\n    manifest = manifest.with_suffix(manifest.suffix + '.sha256')\n    manifest.write_text(f'{digest}  {dest}\\n', encoding='utf-8')\n    print(f'Processed {dest}')\nPY"]