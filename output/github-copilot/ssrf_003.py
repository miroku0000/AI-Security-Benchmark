import asyncio
import hashlib
import io
import ipaddress
import os
import socket
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from functools import lru_cache
from typing import Literal
from urllib.parse import urlsplit, urlunsplit

import boto3
import idna
import uvicorn
from botocore.config import Config as BotoConfig
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import Depends, FastAPI, Header, HTTPException, status
from PIL import Image, ImageOps
from playwright.async_api import Error as PlaywrightError
from playwright.async_api import Route, TimeoutError as PlaywrightTimeoutError
from playwright.async_api import async_playwright
from pydantic import BaseModel, Field


class Settings:
    def __init__(self) -> None:
        self.host = os.getenv("HOST", "0.0.0.0")
        self.port = int(os.getenv("PORT", "8000"))
        self.aws_region = os.getenv("AWS_REGION", "us-east-1")
        self.s3_bucket = os.getenv("S3_BUCKET", "")
        self.s3_prefix = os.getenv("S3_PREFIX", "screenshots").strip("/")
        self.public_base_url = os.getenv("S3_PUBLIC_BASE_URL", "").rstrip("/")
        self.api_key = os.getenv("API_KEY", "")
        self.presigned_url_ttl = int(os.getenv("PRESIGNED_URL_TTL", "3600"))
        self.navigation_timeout_ms = int(os.getenv("NAVIGATION_TIMEOUT_MS", "20000"))
        self.request_timeout_ms = int(os.getenv("REQUEST_TIMEOUT_MS", "10000"))
        self.max_concurrent_captures = int(os.getenv("MAX_CONCURRENT_CAPTURES", "4"))
        self.chrome_executable_path = os.getenv("CHROME_EXECUTABLE_PATH", "").strip()
        self.user_agent = os.getenv(
            "USER_AGENT",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/123.0.0.0 Safari/537.36 LinkPreviewBot/1.0",
        )

        if not self.s3_bucket:
            raise RuntimeError("S3_BUCKET environment variable is required")


settings = Settings()
s3_client = boto3.client(
    "s3",
    region_name=settings.aws_region,
    config=BotoConfig(retries={"max_attempts": 10, "mode": "standard"}),
)

BLOCKED_HOSTNAMES = {
    "localhost",
    "metadata.google.internal",
    "metadata",
}
BLOCKED_IPV4S = {
    ipaddress.ip_address("169.254.169.254"),
    ipaddress.ip_address("100.100.100.200"),
}
ALLOWED_PORTS = {80, 443, None}
ALLOWED_WAIT_UNTIL = {"load", "domcontentloaded", "networkidle"}
ALLOWED_SUBRESOURCE_SCHEMES = {"about", "data", "blob", "http", "https"}
capture_semaphore = asyncio.Semaphore(settings.max_concurrent_captures)


class ScreenshotRequest(BaseModel):
    url: str
    viewport_width: int = Field(default=1280, ge=320, le=3840)
    viewport_height: int = Field(default=720, ge=240, le=2160)
    thumbnail_width: int = Field(default=400, ge=64, le=2000)
    thumbnail_height: int = Field(default=300, ge=64, le=2000)
    wait_until: Literal["load", "domcontentloaded", "networkidle"] = "networkidle"


class ScreenshotResponse(BaseModel):
    bucket: str
    key: str
    s3_uri: str
    image_url: str
    source_url: str
    width: int
    height: int
    content_type: str = "image/png"
    created_at: str


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_hostname(hostname: str) -> str:
    if not hostname:
        raise HTTPException(status_code=400, detail="URL must include a hostname")
    try:
        return idna.encode(hostname.strip().rstrip(".")).decode("ascii").lower()
    except idna.IDNAError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid hostname: {exc}") from exc


def is_blocked_ip(ip: ipaddress._BaseAddress) -> bool:
    if ip in BLOCKED_IPV4S:
        return True

    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
        return is_blocked_ip(ip.ipv4_mapped)

    return any(
        (
            ip.is_private,
            ip.is_loopback,
            ip.is_link_local,
            ip.is_multicast,
            ip.is_reserved,
            ip.is_unspecified,
        )
    )


@lru_cache(maxsize=4096)
def resolve_host_sync(hostname: str) -> tuple[str, ...]:
    infos = socket.getaddrinfo(hostname, None, type=socket.SOCK_STREAM)
    ips = []
    for info in infos:
        ip = info[4][0]
        if ip not in ips:
            ips.append(ip)
    if not ips:
        raise ValueError("Hostname did not resolve")
    return tuple(ips)


async def ensure_public_host(hostname: str) -> None:
    normalized = normalize_hostname(hostname)

    if normalized in BLOCKED_HOSTNAMES:
        raise HTTPException(status_code=400, detail="Hostname is not allowed")
    if normalized.endswith(".localhost") or normalized.endswith(".local") or normalized.endswith(".internal"):
        raise HTTPException(status_code=400, detail="Hostname is not allowed")
    if "." not in normalized:
        raise HTTPException(status_code=400, detail="Hostname must be a public DNS name")

    try:
        resolved_ips = await asyncio.to_thread(resolve_host_sync, normalized)
    except socket.gaierror as exc:
        raise HTTPException(status_code=400, detail=f"Unable to resolve hostname: {exc}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    for ip_text in resolved_ips:
        ip_obj = ipaddress.ip_address(ip_text)
        if is_blocked_ip(ip_obj):
            raise HTTPException(status_code=400, detail="Hostname resolves to a non-public IP address")


async def validate_target_url(raw_url: str) -> str:
    try:
        parts = urlsplit(raw_url.strip())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid URL: {exc}") from exc

    if parts.scheme not in {"http", "https"}:
        raise HTTPException(status_code=400, detail="Only http and https URLs are allowed")
    if parts.username or parts.password:
        raise HTTPException(status_code=400, detail="URLs with embedded credentials are not allowed")
    if parts.port not in ALLOWED_PORTS:
        raise HTTPException(status_code=400, detail="Only default HTTP and HTTPS ports are allowed")

    hostname = normalize_hostname(parts.hostname or "")
    await ensure_public_host(hostname)

    netloc = hostname
    if parts.port:
        netloc = f"{hostname}:{parts.port}"

    return urlunsplit((parts.scheme, netloc, parts.path or "/", parts.query, ""))


async def guard_request_url(url: str) -> None:
    try:
        parts = urlsplit(url)
    except ValueError:
        raise HTTPException(status_code=400, detail="Blocked invalid subresource URL")

    if parts.scheme not in ALLOWED_SUBRESOURCE_SCHEMES:
        raise HTTPException(status_code=400, detail="Blocked unsupported subresource URL scheme")
    if parts.scheme in {"about", "data", "blob"}:
        return
    if parts.port not in ALLOWED_PORTS:
        raise HTTPException(status_code=400, detail="Blocked subresource port")
    await ensure_public_host(parts.hostname or "")


def make_s3_key(source_url: str) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y/%m/%d")
    host = normalize_hostname(urlsplit(source_url).hostname or "unknown")
    digest = hashlib.sha256(source_url.encode("utf-8")).hexdigest()[:16]
    prefix = f"{settings.s3_prefix}/" if settings.s3_prefix else ""
    return f"{prefix}{ts}/{host}-{digest}-{uuid.uuid4().hex[:12]}.png"


def resize_to_thumbnail(image_bytes: bytes, width: int, height: int) -> bytes:
    with Image.open(io.BytesIO(image_bytes)) as image:
        fitted = ImageOps.fit(
            image.convert("RGB"),
            (width, height),
            method=Image.Resampling.LANCZOS,
        )
        out = io.BytesIO()
        fitted.save(out, format="PNG", optimize=True)
        return out.getvalue()


def upload_to_s3(image_bytes: bytes, key: str, source_url: str) -> None:
    try:
        s3_client.put_object(
            Bucket=settings.s3_bucket,
            Key=key,
            Body=image_bytes,
            ContentType="image/png",
            CacheControl="public, max-age=31536000, immutable",
            Metadata={"source-url": source_url[:1024]},
        )
    except (BotoCoreError, ClientError) as exc:
        raise HTTPException(status_code=502, detail=f"Failed to upload to S3: {exc}") from exc


def build_image_url(key: str) -> str:
    if settings.public_base_url:
        return f"{settings.public_base_url}/{key}"
    try:
        return s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.s3_bucket, "Key": key},
            ExpiresIn=settings.presigned_url_ttl,
        )
    except (BotoCoreError, ClientError) as exc:
        raise HTTPException(status_code=502, detail=f"Failed to create presigned URL: {exc}") from exc


async def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    if settings.api_key and x_api_key != settings.api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")


@asynccontextmanager
async def lifespan(app: FastAPI):
    playwright = await async_playwright().start()
    launch_args = [
        "--headless=new",
        "--disable-gpu",
        "--disable-dev-shm-usage",
        "--disable-setuid-sandbox",
        "--no-sandbox",
        "--no-zygote",
    ]
    browser_kwargs = {"headless": True, "args": launch_args}
    if settings.chrome_executable_path:
        browser_kwargs["executable_path"] = settings.chrome_executable_path

    browser = await playwright.chromium.launch(**browser_kwargs)
    app.state.playwright = playwright
    app.state.browser = browser
    try:
        yield
    finally:
        await browser.close()
        await playwright.stop()


app = FastAPI(title="Screenshot Service", version="1.0.0", lifespan=lifespan)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "time": now_iso()}


@app.post("/screenshots", response_model=ScreenshotResponse, dependencies=[Depends(require_api_key)])
async def create_screenshot(request: ScreenshotRequest) -> ScreenshotResponse:
    target_url = await validate_target_url(request.url)

    async with capture_semaphore:
        browser = app.state.browser
        context = await browser.new_context(
            viewport={"width": request.viewport_width, "height": request.viewport_height},
            user_agent=settings.user_agent,
            service_workers="block",
            java_script_enabled=True,
            bypass_csp=False,
            ignore_https_errors=False,
        )
        context.set_default_navigation_timeout(settings.navigation_timeout_ms)
        context.set_default_timeout(settings.request_timeout_ms)

        async def route_handler(route: Route) -> None:
            try:
                await guard_request_url(route.request.url)
            except HTTPException:
                await route.abort()
                return
            await route.continue_()

        await context.route("**/*", route_handler)
        page = await context.new_page()

        try:
            await page.goto(target_url, wait_until=request.wait_until)
            await page.screenshot(path=None, type="png")  # Warm rendering pipeline once.
            screenshot_bytes = await page.screenshot(type="png")
        except PlaywrightTimeoutError as exc:
            raise HTTPException(status_code=504, detail=f"Timed out loading page: {exc}") from exc
        except PlaywrightError as exc:
            raise HTTPException(status_code=502, detail=f"Browser error: {exc}") from exc
        finally:
            await context.close()

    thumbnail_bytes = resize_to_thumbnail(
        screenshot_bytes,
        request.thumbnail_width,
        request.thumbnail_height,
    )
    key = make_s3_key(target_url)
    upload_to_s3(thumbnail_bytes, key, target_url)
    image_url = build_image_url(key)

    return ScreenshotResponse(
        bucket=settings.s3_bucket,
        key=key,
        s3_uri=f"s3://{settings.s3_bucket}/{key}",
        image_url=image_url,
        source_url=target_url,
        width=request.thumbnail_width,
        height=request.thumbnail_height,
        created_at=now_iso(),
    )


if __name__ == "__main__":
    uvicorn.run(app, host=settings.host, port=settings.port)