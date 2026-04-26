import os
import pickle
import hashlib
import logging
import traceback
from datetime import datetime
from typing import Dict, Any, Optional
from functools import wraps
from concurrent.futures import ThreadPoolExecutor
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
import numpy as np

app = Flask(__name__)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

MAX_FILE_SIZE = 500 * 1024 * 1024
ALLOWED_EXTENSIONS = {'.pkl', '.pickle', '.joblib'}
MODEL_STORAGE_BASE = 'model_storage'
MODEL_CACHE_MAX_SIZE = 10

app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE
app.config['UPLOAD_FOLDER'] = MODEL_STORAGE_BASE

if not os.path.exists(MODEL_STORAGE_BASE):
    os.makedirs(MODEL_STORAGE_BASE)

class ModelCache:
    def __init__(self, max_size: int = MODEL_CACHE_MAX_SIZE):
        self.cache: Dict[str, Any] = {}
        self.max_size = max_size
        self.access_order: list = []
    
    def get(self, key: str) -> Optional[Any]:
        if key in self.cache:
            self.access_order.remove(key)
            self.access_order.append(key)
            return self.cache[key]
        return None
    
    def put(self, key: str, value: Any):
        if key in self.cache:
            self.access_order.remove(key)
        elif len(self.cache) >= self.max_size:
            oldest = self.access_order.pop(0)
            del self.cache[oldest]
        self.cache[key] = value
        self.access_order.append(key)
    
    def clear(self, key: str = None):
        if key:
            if key in self.cache:
                self.cache.pop(key)
                self.access_order.remove(key)
        else:
            self.cache.clear()
            self.access_order.clear()

model_cache = ModelCache()
model_executor = ThreadPoolExecutor(max_workers=4)

def validate_tenant(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        tenant_id = request.headers.get('X-Tenant-ID') or request.args.get('tenant_id')
        if not tenant_id:
            return jsonify({'error': 'Missing X-Tenant-ID header or tenant_id parameter'}), 400
        if not isinstance(tenant_id, str) or not (3 <= len(tenant_id) <= 64):
            return jsonify({'error': 'Invalid tenant_id format'}), 400
        if not all(c.isalnum() or c in '_-' for c in tenant_id):
            return jsonify({'error': 'Tenant ID must be alphanumeric with underscores or hyphens'}), 400
        request.tenant_id = tenant_id
        return f(*args, **kwargs)
    return decorated_function

def get_tenant_model_dir(tenant_id: str) -> str:
    return os.path.join(MODEL_STORAGE_BASE, secure_filename(tenant_id))

def ensure_tenant_dir(tenant_id: str):
    tenant_dir = get_tenant_model_dir(tenant_id)
    os.makedirs(tenant_dir, exist_ok=True)
    return tenant_dir

def generate_file_hash(file_content: bytes) -> str:
    return hashlib.sha256(file_content).hexdigest()[:16]

def validate_pickle_file(file_path: str) -> bool:
    try:
        with open(file_path, 'rb') as f:
            pickle.load(f)
        return True
    except Exception as e:
        logger.error(f"Invalid pickle file: {str(e)}")
        return False

def load_model(file_path: str):
    try:
        with open(file_path, 'rb') as f:
            model = pickle.load(f)
        return model
    except Exception as e:
        logger.error(f"Error loading model: {str(e)}")
        raise

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy', 'timestamp': datetime.utcnow().isoformat(), 'service': 'model-serving-api'}), 200

@app.route('/models/upload', methods=['POST'])
@validate_tenant
def upload_model():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    file = request.files['file']
    model_name = request.form.get('model_name')
    if not file or file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    if not model_name:
        return jsonify({'error': 'model_name parameter required'}), 400
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        return jsonify({'error': f'Invalid file type. Allowed: {ALLOWED_EXTENSIONS}'}), 400
    try:
        file_content = file.read()
        if len(file_content) > MAX_FILE_SIZE:
            return jsonify({'error': f'File too large. Max size: {MAX_FILE_SIZE} bytes'}), 413
        file_hash = generate_file_hash(file_content)
        tenant_dir = ensure_tenant_dir(request.tenant_id)
        safe_model_name = secure_filename(model_name)
        if not safe_model_name:
            return jsonify({'error': 'Invalid model name'}), 400
        file_path = os.path.join(tenant_dir, f"{safe_model_name}_{file_hash}.pkl")
        with open(file_path, 'wb') as f:
            f.write(file_content)
        if not validate_pickle_file(file_path):
            os.remove(file_path)
            return jsonify({'error': 'Invalid pickle file format'}), 400
        model_cache.clear(f"{request.tenant_id}:{safe_model_name}")
        logger.info(f"Model uploaded - Tenant: {request.tenant_id}, Model: {safe_model_name}, Path: {file_path}")
        return jsonify({'message': 'Model uploaded successfully', 'tenant_id': request.tenant_id, 'model_name': safe_model_name, 'file_hash': file_hash, 'file_size': len(file_content), 'timestamp': datetime.utcnow().isoformat()}), 201
    except Exception as e:
        logger.error(f"Upload error: {str(e)}\n{traceback.format_exc()}")
        return jsonify({'error': 'Upload failed', 'details': str(e)}), 500

@app.route('/models/list', methods=['GET'])
@validate_tenant
def list_models():
    try:
        tenant_dir = get_tenant_model_dir(request.tenant_id)
        if not os.path.exists(tenant_dir):
            return jsonify({'models': [], 'tenant_id': request.tenant_id}), 200
        models = []
        for filename in os.listdir(tenant_dir):
            if filename.endswith('.pkl'):
                file_path = os.path.join(tenant_dir, filename)
                stat = os.stat(file_path)
                model_name = '_'.join(filename.rsplit('_', 1)[:-1])
                models.append({'model_name': model_name, 'file_name': filename, 'file_size': stat.st_size, 'modified_time': datetime.fromtimestamp(stat.st_mtime).isoformat()})
        return jsonify({'tenant_id': request.tenant_id, 'models': models, 'count': len(models)}), 200
    except Exception as e:
        logger.error(f"List models error: {str(e)}\n{traceback.format_exc()}")
        return jsonify({'error': 'Failed to list models', 'details': str(e)}), 500

@app.route('/models/delete', methods=['DELETE'])
@validate_tenant
def delete_model():
    model_name = request.args.get('model_name')
    if not model_name:
        return jsonify({'error': 'model_name parameter required'}), 400
    try:
        tenant_dir = get_tenant_model_dir(request.tenant_id)
        safe_model_name = secure_filename(model_name)
        if not os.path.exists(tenant_dir):
            return jsonify({'error': 'No models found for this tenant'}), 404
        matching_files = [f for f in os.listdir(tenant_dir) if f.startswith(safe_model_name + '_') and f.endswith('.pkl')]
        if not matching_files:
            return jsonify({'error': f'Model {model_name} not found'}), 404
        deleted_files = []
        for filename in matching_files:
            file_path = os.path.join(tenant_dir, filename)
            os.remove(file_path)
            deleted_files.append(filename)
        model_cache.clear(f"{request.tenant_id}:{safe_model_name}")
        logger.info(f"Model deleted - Tenant: {request.tenant_id}, Model: {safe_model_name}")
        return jsonify({'message': 'Model deleted successfully', 'tenant_id': request.tenant_id, 'model_name': safe_model_name, 'deleted_files': deleted_files}), 200
    except Exception as e:
        logger.error(f"Delete error: {str(e)}\n{traceback.format_exc()}")
        return jsonify({'error': 'Delete failed', 'details': str(e)}), 500

@app.route('/models/predict', methods=['POST'])
@validate_tenant
def predict():
    data = request.get_json()
    if not data or 'model_name' not in data or 'input' not in data:
        return jsonify({'error': 'Missing model_name or input in request body'}), 400
    model_name = data['model_name']
    input_data = data['input']
    try:
        cache_key = f"{request.tenant_id}:{model_name}"
        model = model_cache.get(cache_key)
        if model is None:
            tenant_dir = get_tenant_model_dir(request.tenant_id)
            safe_model_name = secure_filename(model_name)
            if not os.path.exists(tenant_dir):
                return jsonify({'error': 'No models found for this tenant'}), 404
            matching_files = [f for f in os.listdir(tenant_dir) if f.startswith(safe_model_name + '_') and f.endswith('.pkl')]
            if not matching_files:
                return jsonify({'error': f'Model {model_name} not found'}), 404
            latest_file = sorted(matching_files)[-1]
            file_path = os.path.join(tenant_dir, latest_file)
            model = load_model(file_path)
            model_cache.put(cache_key, model)
        if not hasattr(model, 'predict'):
            return jsonify({'error': 'Model does not have predict method'}), 400
        if isinstance(input_data, list):
            input_data = np.array(input_data)
        prediction = model.predict(input_data)
        if isinstance(prediction, np.ndarray):
            prediction = prediction.tolist()
        logger.info(f"Prediction made - Tenant: {request.tenant_id}, Model: {model_name}")
        return jsonify({'tenant_id': request.tenant_id, 'model_name': model_name, 'prediction': prediction, 'timestamp': datetime.utcnow().isoformat()}), 200
    except Exception as e:
        logger.error(f"Prediction error: {str(e)}\n{traceback.format_exc()}")

**model_serving_api.py** (continued):