from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    aws_region: str = "us-east-1"
    s3_bucket: str = ""
    s3_prefix: str = "link-previews/"
    public_base_url: str = ""

    viewport_width: int = 1280
    viewport_height: int = 720
    thumbnail_width: int = 400
    thumbnail_height: int = 225

    screenshot_timeout_ms: int = 30000
    navigation_timeout_ms: int = 45000

    allowed_hosts: str = ""

    @property
    def host_allowlist(self) -> set[str]:
        if not self.allowed_hosts.strip():
            return set()
        return {h.strip().lower() for h in self.allowed_hosts.split(",") if h.strip()}


settings = Settings()

=== models.py ===
from pydantic import BaseModel, HttpUrl


class ScreenshotRequest(BaseModel):
    url: HttpUrl

=== app.py ===
import hashlib
import io
import re
import uuid
from urllib.parse import urlparse

import boto3
from botocore.config import Config
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from PIL import Image
from playwright.async_api import async_playwright

from models import ScreenshotRequest
from settings import settings

app = FastAPI(title="Link Preview Screenshot Service")

_s3 = None


def get_s3():
    global _s3
    if _s3 is None:
        _s3 = boto3.client(
            "s3",
            region_name=settings.aws_region,
            config=Config(signature_version="s3v4"),
        )
    return _s3


PRIVATE_HOST_PATTERNS = (
    re.compile(r"^localhost$", re.I),
    re.compile(r"^127\.", re.I),
    re.compile(r"^169\.254\.", re.I),
    re.compile(r"^10\.", re.I),
    re.compile(r"^172\.(1[6-9]|2[0-9]|3[0-1])\.", re.I),
    re.compile(r"^192\.168\.", re.I),
    re.compile(r"^::1$", re.I),
    re.compile(r"^fe80:", re.I),
    re.compile(r"^fc00:", re.I),
    re.compile(r"^fd", re.I),
)


def validate_target_url(url: str) -> str:
    parsed = urlparse(url.strip())
    if parsed.scheme not in ("http", "https"):
        raise HTTPException(status_code=400, detail="Only http and https URLs are allowed")
    if not parsed.netloc:
        raise HTTPException(status_code=400, detail="Invalid URL")
    host = parsed.hostname
    if not host:
        raise HTTPException(status_code=400, detail="Invalid host")
    h = host.lower()
    if settings.host_allowlist and h not in settings.host_allowlist:
        raise HTTPException(status_code=403, detail="Host not in allowlist")
    for pat in PRIVATE_HOST_PATTERNS:
        if pat.search(h):
            raise HTTPException(status_code=403, detail="Private or local addresses are not allowed")
    return url.strip()


def object_key_for_url(url: str) -> str:
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
    return f"{settings.s3_prefix.rstrip('/')}/{digest}/{uuid.uuid4().hex}.webp"


def resize_to_thumbnail(png_bytes: bytes) -> bytes:
    img = Image.open(io.BytesIO(png_bytes)).convert("RGBA")
    img.thumbnail(
        (settings.thumbnail_width, settings.thumbnail_height),
        Image.Resampling.LANCZOS,
    )
    out = io.BytesIO()
    img.save(out, format="WEBP", quality=82, method=6)
    return out.getvalue()


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/screenshot")
async def screenshot(body: ScreenshotRequest):
    if not settings.s3_bucket:
        raise HTTPException(status_code=500, detail="S3 bucket not configured")

    url = validate_target_url(str(body.url))

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-setuid-sandbox",
            ],
        )
        try:
            context = await browser.new_context(
                viewport={
                    "width": settings.viewport_width,
                    "height": settings.viewport_height,
                },
                ignore_https_errors=True,
            )
            page = await context.new_page()
            page.set_default_timeout(settings.navigation_timeout_ms)
            await page.goto(url, wait_until="networkidle", timeout=settings.navigation_timeout_ms)
            await page.wait_for_timeout(500)
            png_bytes = await page.screenshot(type="png", full_page=False)
        finally:
            await browser.close()

    thumb = resize_to_thumbnail(png_bytes)
    key = object_key_for_url(url)
    s3 = get_s3()
    s3.put_object(
        Bucket=settings.s3_bucket,
        Key=key,
        Body=thumb,
        ContentType="image/webp",
        CacheControl="public, max-age=86400",
    )

    if settings.public_base_url:
        image_url = f"{settings.public_base_url.rstrip('/')}/{key}"
    else:
        image_url = s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.s3_bucket, "Key": key},
            ExpiresIn=604800,
        )

    return JSONResponse(
        {
            "url": url,
            "s3_key": key,
            "image_url": image_url,
        }
    )

=== Dockerfile ===
FROM mcr.microsoft.com/playwright/python:v1.49.1-jammy

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install chromium

COPY settings.py models.py app.py ./

ENV PYTHONUNBUFFERED=1
EXPOSE 8080

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]

=== docker-compose.yml ===
services:
  screenshot:
    build: .
    ports:
      - "8080:8080"
    environment:
      AWS_REGION: ${AWS_REGION:-us-east-1}
      AWS_DEFAULT_REGION: ${AWS_REGION:-us-east-1}
      AWS_ACCESS_KEY_ID: ${AWS_ACCESS_KEY_ID:-}
      AWS_SECRET_ACCESS_KEY: ${AWS_SECRET_ACCESS_KEY:-}
      S3_BUCKET: ${S3_BUCKET}
      S3_PREFIX: ${S3_PREFIX:-link-previews/}
      PUBLIC_BASE_URL: ${PUBLIC_BASE_URL:-}
      ALLOWED_HOSTS: ${ALLOWED_HOSTS:-}
    shm_size: "2gb"

=== ec2-user-data.sh ===
#!/bin/bash
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y docker.io
systemctl enable docker
systemctl start docker
usermod -aG docker ubuntu || true