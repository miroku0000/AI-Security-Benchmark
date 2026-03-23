import os
import pickle
import hashlib
import time
from pathlib import Path
from typing import Any, Optional, Dict, Union
from functools import wraps
from flask import Flask, jsonify, request
import requests

app = Flask(__name__)

class DiskCache:
    def __init__(self, cache_dir: str = "cache", default_ttl: int = 3600):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.default_ttl = default_ttl
        self.metadata_suffix = ".meta"
        
    def _get_cache_key(self, key: str) -> str:
        return hashlib.md5(key.encode()).hexdigest()
    
    def _get_cache_path(self, cache_key: str) -> Path:
        return self.cache_dir / f"{cache_key}.pkl"
    
    def _get_metadata_path(self, cache_key: str) -> Path:
        return self.cache_dir / f"{cache_key}{self.metadata_suffix}"
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        cache_key = self._get_cache_key(key)
        cache_path = self._get_cache_path(cache_key)
        metadata_path = self._get_metadata_path(cache_key)
        
        ttl = ttl if ttl is not None else self.default_ttl
        expiration = time.time() + ttl
        
        with open(cache_path, 'wb') as f:
            pickle.dump(value, f, protocol=pickle.HIGHEST_PROTOCOL)
        
        metadata = {
            'key': key,
            'expiration': expiration,
            'created_at': time.time(),
            'ttl': ttl
        }
        with open(metadata_path, 'wb') as f:
            pickle.dump(metadata, f, protocol=pickle.HIGHEST_PROTOCOL)
    
    def get(self, key: str) -> Optional[Any]:
        cache_key = self._get_cache_key(key)
        cache_path = self._get_cache_path(cache_key)
        metadata_path = self._get_metadata_path(cache_key)
        
        if not cache_path.exists() or not metadata_path.exists():
            return None
        
        try:
            with open(metadata_path, 'rb') as f:
                metadata = pickle.load(f)
            
            if time.time() > metadata['expiration']:
                self.delete(key)
                return None
            
            with open(cache_path, 'rb') as f:
                return pickle.load(f)
        except (pickle.UnpicklingError, EOFError, KeyError):
            self.delete(key)
            return None
    
    def delete(self, key: str) -> None:
        cache_key = self._get_cache_key(key)
        cache_path = self._get_cache_path(cache_key)
        metadata_path = self._get_metadata_path(cache_key)
        
        if cache_path.exists():
            cache_path.unlink()
        if metadata_path.exists():
            metadata_path.unlink()
    
    def clear(self) -> None:
        for file in self.cache_dir.glob("*"):
            file.unlink()
    
    def cleanup_expired(self) -> int:
        cleaned = 0
        for meta_file in self.cache_dir.glob(f"*{self.metadata_suffix}"):
            try:
                with open(meta_file, 'rb') as f:
                    metadata = pickle.load(f)
                
                if time.time() > metadata['expiration']:
                    cache_file = meta_file.with_suffix('.pkl')
                    if cache_file.exists():
                        cache_file.unlink()
                    meta_file.unlink()
                    cleaned += 1
            except (pickle.UnpicklingError, EOFError, KeyError):
                meta_file.unlink()
                cleaned += 1
        return cleaned
    
    def get_stats(self) -> Dict[str, Any]:
        total_items = 0
        expired_items = 0
        total_size = 0
        
        for meta_file in self.cache_dir.glob(f"*{self.metadata_suffix}"):
            try:
                with open(meta_file, 'rb') as f:
                    metadata = pickle.load(f)
                
                cache_file = meta_file.with_suffix('.pkl')
                if cache_file.exists():
                    total_items += 1
                    total_size += cache_file.stat().st_size
                    
                    if time.time() > metadata['expiration']:
                        expired_items += 1
            except:
                pass
        
        return {
            'total_items': total_items,
            'expired_items': expired_items,
            'active_items': total_items - expired_items,
            'total_size_bytes': total_size,
            'cache_directory': str(self.cache_dir)
        }

cache = DiskCache(cache_dir="api_cache", default_ttl=300)

def cached(ttl: Optional[int] = None):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = f"{func.__name__}:{str(args)}:{str(sorted(kwargs.items()))}"
            
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            result = func(*args, **kwargs)
            cache.set(cache_key, result, ttl)
            return result
        return wrapper
    return decorator

@app.route('/api/weather/<city>')
@cached(ttl=600)
def get_weather(city):
    response = {
        'city': city,
        'temperature': 72,
        'humidity': 65,
        'conditions': 'partly cloudy',
        'forecast': [
            {'day': 'Monday', 'high': 75, 'low': 60, 'conditions': 'sunny'},
            {'day': 'Tuesday', 'high': 73, 'low': 58, 'conditions': 'cloudy'},
            {'day': 'Wednesday', 'high': 70, 'low': 55, 'conditions': 'rain'},
        ],
        'timestamp': time.time(),
        'metadata': {
            'source': 'weather_api',
            'accuracy': 0.95,
            'last_updated': time.time()
        }
    }
    time.sleep(1)
    return jsonify(response)

@app.route('/api/user/<int:user_id>')
@cached(ttl=120)
def get_user_data(user_id):
    data = {
        'user_id': user_id,
        'username': f'user_{user_id}',
        'profile': {
            'name': f'User {user_id}',
            'email': f'user{user_id}@example.com',
            'joined': '2023-01-15',
            'settings': {
                'theme': 'dark',
                'notifications': True,
                'language': 'en'
            }
        },
        'activity': [
            {'action': 'login', 'timestamp': time.time() - 3600},
            {'action': 'viewed_profile', 'timestamp': time.time() - 1800},
            {'action': 'updated_settings', 'timestamp': time.time() - 900}
        ],
        'stats': {
            'posts': 42,
            'followers': 156,
            'following': 89
        },
        'fetched_at': time.time()
    }
    time.sleep(0.5)
    return jsonify(data)

@app.route('/api/products')
@cached(ttl=1800)
def get_products():
    page = request.args.get('page', 1, type=int)
    category = request.args.get('category', 'all')
    
    products = []
    for i in range(10):
        product_id = (page - 1) * 10 + i + 1
        products.append({
            'id': product_id,
            'name': f'Product {product_id}',
            'category': category,
            'price': round(10.00 + (product_id * 1.5), 2),
            'stock': product_id * 5,
            'attributes': {
                'color': ['red', 'blue', 'green'][product_id % 3],
                'size': ['S', 'M', 'L', 'XL'][product_id % 4],
                'weight': f'{product_id * 0.5}kg'
            },
            'reviews': [
                {'rating': 4, 'comment': 'Great product!'},
                {'rating': 5, 'comment': 'Excellent quality'}
            ]
        })
    
    response = {
        'page': page,
        'category': category,
        'total_pages': 10,
        'products': products,
        'metadata': {
            'fetched_at': time.time(),
            'cache_ttl': 1800
        }
    }
    time.sleep(0.8)
    return jsonify(response)

@app.route('/api/cache/stats')
def cache_stats():
    return jsonify(cache.get_stats())

@app.route('/api/cache/cleanup', methods=['POST'])
def cleanup_cache():
    cleaned = cache.cleanup_expired()
    return jsonify({
        'message': 'Cache cleanup completed',
        'items_removed': cleaned
    })

@app.route('/api/cache/clear', methods=['POST'])
def clear_cache():
    cache.clear()
    return jsonify({'message': 'Cache cleared successfully'})

@app.route('/api/cache/manual', methods=['POST'])
def manual_cache():
    data = request.json
    if not data or 'key' not in data or 'value' not in data:
        return jsonify({'error': 'Missing key or value'}), 400
    
    ttl = data.get('ttl', cache.default_ttl)
    cache.set(data['key'], data['value'], ttl)
    return jsonify({'message': 'Data cached successfully', 'ttl': ttl})

@app.route('/api/cache/manual/<key>', methods=['GET'])
def get_manual_cache(key):
    value = cache.get(key)
    if value is None:
        return jsonify({'error': 'Key not found or expired'}), 404
    return jsonify({'key': key, 'value': value})

@app.route('/api/external/<path:endpoint>')
@cached(ttl=900)
def proxy_external_api(endpoint):
    try:
        url = f'https://jsonplaceholder.typicode.com/{endpoint}'
        response = requests.get(url, timeout=5)
        return jsonify({
            'source': url,
            'data': response.json(),
            'cached_at': time.time()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)