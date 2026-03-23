from __future__ import annotations

import hashlib
import io
import os
import re
from typing import Optional
from urllib.parse import urlparse

import boto3
from fastapi import FastAPI, HTTPException
from PIL import Image
from playwright.sync_api import sync_playwright
from pydantic import BaseModel, Field, HttpUrl

S3_BUCKET = os.environ["S3_BUCKET"]
S3_PREFIX = os.environ.get("S3_PREFIX", "link-previews/")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL", "").rstrip("/")
VIEWPORT_WIDTH = int(os.environ.get("VIEWPORT_WIDTH", "1280"))
VIEWPORT_HEIGHT = int(os.environ.get("VIEWPORT_HEIGHT", "720"))
THUMB_MAX_WIDTH = int(os.environ.get("THUMB_MAX_WIDTH", "400"))
THUMB_MAX_HEIGHT = int(os.environ.get("THUMB_MAX_HEIGHT", "225"))
SCREENSHOT_TIMEOUT_MS = int(os.environ.get("SCREENSHOT_TIMEOUT_MS", "30000"))
NAVIGATION_TIMEOUT_MS = int(os.environ.get("NAVIGATION_TIMEOUT_MS", "30000"))
ALLOWED_SCHEMES = frozenset({"http", "https"})
BLOCKED_HOSTS = frozenset(
    h.strip().lower()
    for h in os.environ.get("BLOCKED_HOSTS", "localhost,127.0.0.1,0.0.0.0,::1").split(",")
    if h.strip()
)

s3 = boto3.client("s3", region_name=AWS_REGION)
app = FastAPI(title="Link preview screenshot service")


class ScreenshotRequest(BaseModel):
    url: HttpUrl = Field(..., description="Page to capture")


class ScreenshotResponse(BaseModel):
    s3_key: str
    public_url: Optional[str]


def _validate_target_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme.lower() not in ALLOWED_SCHEMES:
        raise HTTPException(status_code=400, detail="Only http and https URLs are allowed")
    host = (parsed.hostname or "").lower()
    if not host or host in BLOCKED_HOSTS:
        raise HTTPException(status_code=400, detail="Host not allowed")
    if re.match(r"^(127\.|10\.|192\.168\.|172\.(1[6-9]|2[0-9]|3[01])\.)\d", host):
        raise HTTPException(status_code=400, detail="Private network addresses are not allowed")


def _object_key_for_url(url: str) -> str:
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:32]
    safe = re.sub(r"[^a-zA-Z0-9._-]+", "_", urlparse(url).netloc)[:80] or "page"
    return f"{S3_PREFIX.rstrip('/')}/{safe}/{digest}.webp"


def _thumbnail_webp(png_bytes: bytes) -> bytes:
    with Image.open(io.BytesIO(png_bytes)) as im:
        im = im.convert("RGB")
        im.thumbnail((THUMB_MAX_WIDTH, THUMB_MAX_HEIGHT), Image.Resampling.LANCZOS)
        buf = io.BytesIO()
        im.save(buf, format="WEBP", quality=82, method=6)
        return buf.getvalue()


def _capture_png(url: str) -> bytes:
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-setuid-sandbox",
            ],
        )
        try:
            context = browser.new_context(
                viewport={"width": VIEWPORT_WIDTH, "height": VIEWPORT_HEIGHT},
                user_agent=(
                    "Mozilla/5.0 (compatible; LinkPreviewBot/1.0; "
                    "+https://example.com/bot) AppleWebKit/537.36"
                ),
            )
            page = context.new_page()
            page.set_default_navigation_timeout(NAVIGATION_TIMEOUT_MS)
            page.set_default_timeout(SCREENSHOT_TIMEOUT_MS)
            page.goto(url, wait_until="load", timeout=NAVIGATION_TIMEOUT_MS)
            png = page.screenshot(type="png", full_page=False)
            context.close()
            return png
        finally:
            browser.close()


def _upload_webp(key: str, body: bytes, content_type: str = "image/webp") -> None:
    kwargs = {
        "Bucket": S3_BUCKET,
        "Key": key,
        "Body": body,
        "ContentType": content_type,
    }
    if PUBLIC_BASE_URL:
        kwargs["CacheControl"] = "public, max-age=86400"
    s3.put_object(**kwargs)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/screenshot", response_model=ScreenshotResponse)
def screenshot(req: ScreenshotRequest):
    url_str = str(req.url)
    _validate_target_url(url_str)
    key = _object_key_for_url(url_str)
    try:
        png = _capture_png(url_str)
        webp = _thumbnail_webp(png)
        _upload_webp(key, webp)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Capture failed: {e!s}") from e

    public_url = None
    if PUBLIC_BASE_URL:
        public_url = f"{PUBLIC_BASE_URL}/{key}"

    return ScreenshotResponse(s3_key=key, public_url=public_url)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app:app",
        host=os.environ.get("HOST", "0.0.0.0"),
        port=int(os.environ.get("PORT", "8000")),
        workers=int(os.environ.get("UVICORN_WORKERS", "1")),
    )
