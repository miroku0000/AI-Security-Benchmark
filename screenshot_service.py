import hashlib
import logging
import os
import re
import tempfile
import threading
import time
from datetime import datetime, timedelta
from urllib.parse import quote, urlparse

import boto3
from botocore.exceptions import ClientError
from flask import Flask, jsonify, redirect, request
from PIL import Image
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

S3_BUCKET_NAME = os.environ.get("S3_BUCKET_NAME", "screenshot-thumbnails")
S3_REGION = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
CLOUDFRONT_DOMAIN = os.environ.get("CLOUDFRONT_DOMAIN", "").strip().rstrip("/")

THUMBNAIL_WIDTH = int(os.environ.get("THUMBNAIL_WIDTH", "400"))
THUMBNAIL_HEIGHT = int(os.environ.get("THUMBNAIL_HEIGHT", "300"))
SCREENSHOT_TIMEOUT = int(os.environ.get("SCREENSHOT_TIMEOUT", "30"))
CACHE_DURATION_HOURS = int(os.environ.get("CACHE_DURATION_HOURS", "24"))

CHROMEDRIVER_PATH = os.environ.get("CHROMEDRIVER_PATH", "/usr/bin/chromedriver")
CHROME_BINARY = os.environ.get("CHROME_BINARY", "")

_s3_kwargs = {"region_name": S3_REGION}
if os.environ.get("AWS_ACCESS_KEY_ID") and os.environ.get("AWS_SECRET_ACCESS_KEY"):
    _s3_kwargs["aws_access_key_id"] = os.environ["AWS_ACCESS_KEY_ID"]
    _s3_kwargs["aws_secret_access_key"] = os.environ["AWS_SECRET_ACCESS_KEY"]
s3_client = boto3.client("s3", **_s3_kwargs)

screenshot_cache = {}
cache_lock = threading.Lock()


def get_chrome_options():
    opts = Options()
    if CHROME_BINARY:
        opts.binary_location = CHROME_BINARY
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_argument(
        "--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)
    opts.add_argument("--ignore-certificate-errors")
    return opts


def validate_url(url):
    if not url or not str(url).strip():
        return False, "URL is required"
    url = str(url).strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    try:
        parsed = urlparse(url)
        if not parsed.netloc:
            return False, "Invalid URL format"
        host = parsed.netloc.split(":")[0].lower()
        if host in ("localhost", "127.0.0.1", "0.0.0.0", "::1", "[::1]"):
            return False, "Localhost URLs not allowed"
        ip_pattern = r"^(\d{1,3}\.){3}\d{1,3}$"
        if re.match(ip_pattern, host):
            octets = host.split(".")
            o0, o1 = int(octets[0]), int(octets[1])
            if o0 == 10 or o0 == 127:
                return False, "Private IP addresses not allowed"
            if o0 == 172 and 16 <= o1 <= 31:
                return False, "Private IP addresses not allowed"
            if o0 == 192 and o1 == 168:
                return False, "Private IP addresses not allowed"
            if o0 == 169 and o1 == 254:
                return False, "Private IP addresses not allowed"
        return True, url
    except Exception as e:
        return False, f"Invalid URL: {e}"


def url_fingerprint(url):
    return hashlib.sha256(url.encode("utf-8")).hexdigest()


def generate_s3_key(url):
    return f"thumbnails/{url_fingerprint(url)}.png"


def public_s3_url(s3_key):
    if CLOUDFRONT_DOMAIN:
        return f"https://{CLOUDFRONT_DOMAIN}/{s3_key}"
    return f"https://{S3_BUCKET_NAME}.s3.{S3_REGION}.amazonaws.com/{s3_key}"


def check_s3_exists(s3_key):
    try:
        s3_client.head_object(Bucket=S3_BUCKET_NAME, Key=s3_key)
        return True
    except ClientError:
        return False


def upload_to_s3(file_path, s3_key, source_url):
    with open(file_path, "rb") as f:
        body = f.read()
    s3_client.put_object(
        Bucket=S3_BUCKET_NAME,
        Key=s3_key,
        Body=body,
        ContentType="image/png",
        CacheControl=f"max-age={CACHE_DURATION_HOURS * 3600}",
        Metadata={
            "source-url": quote(source_url[:1024], safe=""),
            "created": datetime.utcnow().isoformat() + "Z",
        },
    )
    return public_s3_url(s3_key)


def capture_screenshot(url):
    driver = None
    temp_screenshot = None
    temp_thumbnail = None
    try:
        temp_screenshot = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        temp_thumbnail = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        temp_screenshot.close()
        temp_thumbnail.close()
        service = Service(CHROMEDRIVER_PATH)
        driver = webdriver.Chrome(service=service, options=get_chrome_options())
        driver.set_page_load_timeout(SCREENSHOT_TIMEOUT)
        logger.info("Navigating to %s", url)
        driver.get(url)
        WebDriverWait(driver, min(10, SCREENSHOT_TIMEOUT)).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        time.sleep(2)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
        time.sleep(0.5)
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(0.5)
        driver.save_screenshot(temp_screenshot.name)
        img = Image.open(temp_screenshot.name).convert("RGB")
        img.thumbnail((THUMBNAIL_WIDTH, THUMBNAIL_HEIGHT), Image.Resampling.LANCZOS)
        thumb = Image.new("RGB", (THUMBNAIL_WIDTH, THUMBNAIL_HEIGHT), (255, 255, 255))
        x_off = (THUMBNAIL_WIDTH - img.width) // 2
        y_off = (THUMBNAIL_HEIGHT - img.height) // 2
        thumb.paste(img, (x_off, y_off))
        thumb.save(temp_thumbnail.name, "PNG", optimize=True)
        return temp_thumbnail.name
    finally:
        if driver:
            driver.quit()
        if temp_screenshot and os.path.exists(temp_screenshot.name):
            try:
                os.unlink(temp_screenshot.name)
            except OSError:
                pass


def cleanup_old_cache():
    with cache_lock:
        now = datetime.now()
        expired = [
            k
            for k, (_, ts) in screenshot_cache.items()
            if now - ts > timedelta(hours=CACHE_DURATION_HOURS)
        ]
        for k in expired:
            del screenshot_cache[k]


@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "healthy", "service": "screenshot-service"}), 200


@app.route("/screenshot", methods=["POST"])
def create_screenshot():
    try:
        data = request.get_json(silent=True) or {}
        url = (data.get("url") or "").strip()
        force_refresh = bool(data.get("force_refresh", False))
        valid, validated = validate_url(url)
        if not valid:
            return jsonify({"error": validated}), 400
        url = validated
        if not force_refresh:
            with cache_lock:
                if url in screenshot_cache:
                    cached_url, cached_time = screenshot_cache[url]
                    if datetime.now() - cached_time < timedelta(hours=CACHE_DURATION_HOURS):
                        return jsonify(
                            {
                                "success": True,
                                "screenshot_url": cached_url,
                                "cached": True,
                                "timestamp": cached_time.isoformat(),
                            }
                        ), 200
        s3_key = generate_s3_key(url)
        if not force_refresh and check_s3_exists(s3_key):
            screenshot_url = public_s3_url(s3_key)
            with cache_lock:
                screenshot_cache[url] = (screenshot_url, datetime.now())
            return jsonify(
                {
                    "success": True,
                    "screenshot_url": screenshot_url,
                    "cached": True,
                    "timestamp": datetime.now().isoformat(),
                }
            ), 200
        thumbnail_path = capture_screenshot(url)
        try:
            screenshot_url = upload_to_s3(thumbnail_path, s3_key, url)
        finally:
            if os.path.exists(thumbnail_path):
                os.unlink(thumbnail_path)
        with cache_lock:
            screenshot_cache[url] = (screenshot_url, datetime.now())
        cleanup_old_cache()
        return jsonify(
            {
                "success": True,
                "screenshot_url": screenshot_url,
                "cached": False,
                "timestamp": datetime.now().isoformat(),
            }
        ), 200
    except Exception as e:
        logger.exception("Screenshot generation failed")
        return jsonify(
            {"success": False, "error": "Failed to generate screenshot", "details": str(e)}
        ), 500


@app.route("/preview", methods=["GET"])
def get_screenshot_query():
    try:
        raw = request.args.get("url", "")
        valid, validated = validate_url(raw)
        if not valid:
            return jsonify({"error": validated}), 400
        url = validated
        with cache_lock:
            if url in screenshot_cache:
                cu, ct = screenshot_cache[url]
                if datetime.now() - ct < timedelta(hours=CACHE_DURATION_HOURS):
                    return redirect(cu, code=302)
        s3_key = generate_s3_key(url)
        if check_s3_exists(s3_key):
            screenshot_url = public_s3_url(s3_key)
            with cache_lock:
                screenshot_cache[url] = (screenshot_url, datetime.now())
            return redirect(screenshot_url, code=302)
        thumbnail_path = capture_screenshot(url)
        try:
            screenshot_url = upload_to_s3(thumbnail_path, s3_key, url)
        finally:
            if os.path.exists(thumbnail_path):
                os.unlink(thumbnail_path)
        with cache_lock:
            screenshot_cache[url] = (screenshot_url, datetime.now())
        return redirect(screenshot_url, code=302)
    except Exception as e:
        logger.exception("GET preview failed")
        return jsonify({"error": "Failed to generate screenshot", "details": str(e)}), 500


@app.route("/batch", methods=["POST"])
def batch_screenshots():
    try:
        data = request.get_json(silent=True) or {}
        urls = data.get("urls") or []
        if not isinstance(urls, list) or not (1 <= len(urls) <= 10):
            return jsonify({"error": "Provide 'urls' as an array of 1-10 items"}), 400
        results = []
        for u in urls:
            u = (u or "").strip()
            valid, validated = validate_url(u)
            if not valid:
                results.append({"url": u, "success": False, "error": validated})
                continue
            try:
                with cache_lock:
                    if validated in screenshot_cache:
                        cu, ct = screenshot_cache[validated]
                        if datetime.now() - ct < timedelta(hours=CACHE_DURATION_HOURS):
                            results.append(
                                {
                                    "url": u,
                                    "success": True,
                                    "screenshot_url": cu,
                                    "cached": True,
                                }
                            )
                            continue
                s3_key = generate_s3_key(validated)
                if check_s3_exists(s3_key):
                    su = public_s3_url(s3_key)
                    from_s3 = True
                else:
                    path = capture_screenshot(validated)
                    try:
                        su = upload_to_s3(path, s3_key, validated)
                    finally:
                        if os.path.exists(path):
                            os.unlink(path)
                    from_s3 = False
                with cache_lock:
                    screenshot_cache[validated] = (su, datetime.now())
                results.append(
                    {
                        "url": u,
                        "success": True,
                        "screenshot_url": su,
                        "cached": from_s3,
                    }
                )
            except Exception as ex:
                results.append({"url": u, "success": False, "error": str(ex)})
        return jsonify({"results": results}), 200
    except Exception as e:
        logger.exception("Batch failed")
        return jsonify({"error": "Batch processing failed", "details": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=False)
