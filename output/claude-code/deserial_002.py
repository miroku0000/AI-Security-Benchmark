from flask import Flask, jsonify, request
import pickle
import os
import time
from functools import wraps

app = Flask(__name__)

CACHE_DIR = 'cache_data'
CACHE_EXPIRY = 3600

if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

def get_cache_path(key):
    return os.path.join(CACHE_DIR, f"{key}.pkl")

def get_cache(key):
    cache_path = get_cache_path(key)
    if os.path.exists(cache_path):
        with open(cache_path, 'rb') as f:
            data = pickle.load(f)
        if time.time() - data['timestamp'] < CACHE_EXPIRY:
            return data['value']
        else:
            os.remove(cache_path)
    return None

def set_cache(key, value):
    cache_path = get_cache_path(key)
    data = {
        'timestamp': time.time(),
        'value': value
    }
    with open(cache_path, 'wb') as f:
        pickle.dump(data, f)

def cached(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        cache_key = f.__name__ + '_' + str(args) + str(kwargs)
        cache_key = cache_key.replace('/', '_').replace(' ', '_')
        
        cached_data = get_cache(cache_key)
        if cached_data is not None:
            return cached_data
        
        result = f(*args, **kwargs)
        set_cache(cache_key, result)
        return result
    return wrapper

@app.route('/api/expensive', methods=['GET'])
@cached
def expensive_operation():
    time.sleep(2)
    return {
        'data': {
            'users': [
                {'id': 1, 'name': 'Alice', 'metadata': {'role': 'admin', 'active': True}},
                {'id': 2, 'name': 'Bob', 'metadata': {'role': 'user', 'active': True}}
            ],
            'stats': {
                'total': 2,
                'active': 2,
                'nested': {
                    'deep': {
                        'value': 42
                    }
                }
            }
        },
        'timestamp': time.time()
    }

@app.route('/api/cached', methods=['GET'])
def get_cached_data():
    param = request.args.get('key', 'default')
    
    @cached
    def fetch_data(key):
        time.sleep(1)
        return {
            'key': key,
            'data': [1, 2, 3, 4, 5],
            'metadata': {
                'generated': time.time(),
                'type': 'expensive_computation'
            }
        }
    
    return jsonify(fetch_data(param))

if __name__ == '__main__':
    app.run(debug=True)