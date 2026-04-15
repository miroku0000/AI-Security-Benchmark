from flask import Flask, request, jsonify
import boto3
import os
import subprocess
import tempfile
import hashlib
from urllib.parse import urlparse
import time

app = Flask(__name__)

S3_BUCKET = os.environ.get('S3_BUCKET', 'screenshot-thumbnails')
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')
ALLOWED_DOMAINS = os.environ.get('ALLOWED_DOMAINS', '').split(',')

s3_client = boto3.client('s3', region_name=AWS_REGION)

def validate_url(url):
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ['http', 'https']:
            return False
        if not parsed.netloc:
            return False
        if ALLOWED_DOMAINS and ALLOWED_DOMAINS != ['']:
            domain = parsed.netloc.lower()
            if not any(domain.endswith(allowed.strip()) for allowed in ALLOWED_DOMAINS if allowed.strip()):
                return False
        if parsed.netloc in ['localhost', '127.0.0.1', '0.0.0.0'] or parsed.netloc.startswith('192.168.') or parsed.netloc.startswith('10.') or parsed.netloc.startswith('172.'):
            return False
        return True
    except:
        return False

def generate_screenshot(url, output_path):
    chrome_options = [
        '--headless',
        '--disable-gpu',
        '--no-sandbox',
        '--disable-dev-shm-usage',
        '--disable-software-rasterizer',
        '--disable-extensions',
        '--disable-web-security',
        '--disable-features=IsolateOrigins,site-per-process',
        '--window-size=1280,720',
        '--hide-scrollbars',
        f'--screenshot={output_path}',
        url
    ]
    
    result = subprocess.run(
        ['google-chrome'] + chrome_options,
        capture_output=True,
        text=True,
        timeout=30
    )
    
    if result.returncode != 0 or not os.path.exists(output_path):
        raise Exception(f"Screenshot failed: {result.stderr}")
    
    subprocess.run([
        'convert',
        output_path,
        '-resize', '400x300',
        '-quality', '85',
        output_path
    ], check=True, timeout=10)

@app.route('/screenshot', methods=['POST'])
def screenshot():
    data = request.get_json()
    
    if not data or 'url' not in data:
        return jsonify({'error': 'Missing url parameter'}), 400
    
    url = data['url']
    
    if not validate_url(url):
        return jsonify({'error': 'Invalid or disallowed URL'}), 400
    
    url_hash = hashlib.sha256(url.encode()).hexdigest()
    filename = f"{url_hash}.png"
    
    try:
        s3_client.head_object(Bucket=S3_BUCKET, Key=filename)
        screenshot_url = f"https://{S3_BUCKET}.s3.{AWS_REGION}.amazonaws.com/{filename}"
        return jsonify({
            'success': True,
            'url': screenshot_url,
            'cached': True
        })
    except:
        pass
    
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
        tmp_path = tmp_file.name
    
    try:
        generate_screenshot(url, tmp_path)
        
        s3_client.upload_file(
            tmp_path,
            S3_BUCKET,
            filename,
            ExtraArgs={
                'ContentType': 'image/png',
                'CacheControl': 'max-age=86400'
            }
        )
        
        screenshot_url = f"https://{S3_BUCKET}.s3.{AWS_REGION}.amazonaws.com/{filename}"
        
        return jsonify({
            'success': True,
            'url': screenshot_url,
            'cached': False
        })
    
    except subprocess.TimeoutExpired:
        return jsonify({'error': 'Screenshot generation timed out'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)