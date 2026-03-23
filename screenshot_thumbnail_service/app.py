import hashlib
import io
import logging
import os
import re
from urllib.parse import urlparse

import boto3
from botocore.exceptions import ClientError
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
from playwright.sync_api import sync_playwright
from pydantic import BaseModel, Field, HttpUrl
from pydantic_settings import BaseSettings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    s3_bucket: str = Field(..., alias="S3_BUCKET")
    aws_region: str = Field(default="us-east-1", alias="AWS_REGION")
    s3_prefix: str = Field(default="link-previews/", alias="S3_PREFIX")
    public_base_url: str | None = Field(default=None, alias="PUBLIC_BASE_URL")
    viewport_width: int = Field(default=1280, alias="VIEWPORT_WIDTH")
    viewport_height: int = Field(default=720, alias="VIEWPORT_HEIGHT")
    thumb_width: int = Field(default=400, alias="THUMB_WIDTH")
    thumb_height: int = Field(default=225, alias="THUMB_HEIGHT")
    navigation_timeout_ms: int = Field(default=30000, alias="NAVIGATION_TIMEOUT_MS")
    allowed_hosts: str | None = Field(default=None, alias="ALLOWED_HOSTS")
    cors_origins: str = Field(default="*", alias="CORS_ORIGINS")

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
app = FastAPI(title="Screenshot Thumbnail Service")

_origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins if _origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_s3 = boto3.client("s3", region_name=settings.aws_region)


class ScreenshotRequest(BaseModel):
    url: HttpUrl
    force_refresh: bool = False


class ScreenshotResponse(BaseModel):
    s3_key: str
    s3_uri: str
    preview_url: str | None
    content_type: str = "image/png"


def _normalize_url(url: str) -> str:
    u = url.strip()
    if not u.startswith(("http://", "https://")):
        u = "https://" + u
    return u


def _url_allowed(url: str) -> bool:
    if not settings.allowed_hosts:
        return True
    allowed = {h.strip().lower() for h in settings.allowed_hosts.split(",") if h.strip()}
    host = urlparse(url).hostname
    if not host:
        return False
    return host.lower() in allowed


def _object_key_for_url(url: str) -> str:
    h = hashlib.sha256(url.encode("utf-8")).hexdigest()
    base = settings.s3_prefix.rstrip("/") + "/"
    return f"{base}{h}.png"


def _public_url(key: str) -> str | None:
    if settings.public_base_url:
        base = settings.public_base_url.rstrip("/")
        return f"{base}/{key}"
    try:
        return _s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.s3_bucket, "Key": key},
            ExpiresIn=86400,
        )
    except ClientError:
        return None


def _screenshot_to_thumbnail_png(page_url: str) -> bytes:
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
            ],
        )
        try:
            context = browser.new_context(
                viewport={
                    "width": settings.viewport_width,
                    "height": settings.viewport_height,
                },
                ignore_https_errors=True,
            )
            page = context.new_page()
            page.set_default_navigation_timeout(settings.navigation_timeout_ms)
            page.goto(page_url, wait_until="domcontentloaded", timeout=settings.navigation_timeout_ms)
            page.wait_for_timeout(500)
            png = page.screenshot(type="png", full_page=False)
        finally:
            browser.close()
    img = Image.open(io.BytesIO(png)).convert("RGB")
    img.thumbnail((settings.thumb_width, settings.thumb_height), Image.Resampling.LANCZOS)
    out = io.BytesIO()
    img.save(out, format="PNG", optimize=True)
    return out.getvalue()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/screenshot", response_model=ScreenshotResponse)
def create_screenshot(body: ScreenshotRequest):
    raw = str(body.url)
    url = _normalize_url(raw)
    if not re.match(r"^https?://", url, re.I):
        raise HTTPException(status_code=400, detail="Only http and https URLs are allowed")
    if not _url_allowed(url):
        raise HTTPException(status_code=403, detail="Host not allowed")

    key = _object_key_for_url(url)
    if not body.force_refresh:
        try:
            _s3.head_object(Bucket=settings.s3_bucket, Key=key)
            preview = _public_url(key)
            return ScreenshotResponse(
                s3_key=key,
                s3_uri=f"s3://{settings.s3_bucket}/{key}",
                preview_url=preview,
            )
        except ClientError as e:
            code = e.response.get("Error", {}).get("Code", "")
            if code not in ("404", "NotFound", "NoSuchKey"):
                logger.exception("S3 head_object failed")
                raise HTTPException(status_code=502, detail="Storage error") from e

    try:
        png_bytes = _screenshot_to_thumbnail_png(url)
    except Exception as e:
        logger.exception("Screenshot failed")
        raise HTTPException(status_code=502, detail="Screenshot failed") from e

    try:
        _s3.put_object(
            Bucket=settings.s3_bucket,
            Key=key,
            Body=png_bytes,
            ContentType="image/png",
            CacheControl="public, max-age=86400",
        )
    except ClientError as e:
        logger.exception("S3 put_object failed")
        raise HTTPException(status_code=502, detail="Upload failed") from e

    preview = _public_url(key)
    return ScreenshotResponse(
        s3_key=key,
        s3_uri=f"s3://{settings.s3_bucket}/{key}",
        preview_url=preview,
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app:app",
        host=os.environ.get("HOST", "0.0.0.0"),
        port=int(os.environ.get("PORT", "8080")),
    )
