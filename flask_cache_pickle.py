import pickle
import os
import time
from functools import wraps
from flask import Flask, jsonify, request
import hashlib

app = Flask(__name__)

CACHE_DIR = 'cache'
DEFAULT_EXPIRATION = 3600  # 1 hour in seconds

if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

def get_cache_key(endpoint, params):
    key_string = f"{endpoint}_{str(sorted(params.items()))}"
    return hashlib.md5(key_string.encode()).hexdigest()

def disk_cache(expiration=DEFAULT_EXPIRATION):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = get_cache_key(request.endpoint, request.args.to_dict())
            cache_file = os.path.join(CACHE_DIR, f"{cache_key}.pkl")
            
            if os.path.exists(cache_file):
                with open(cache_file, 'rb') as f:
                    cached_data = pickle.load(f)
                    if time.time() - cached_data['timestamp'] < expiration:
                        return cached_data['data']
            
            result = func(*args, **kwargs)
            
            cache_data = {
                'data': result,
                'timestamp': time.time()
            }
            
            with open(cache_file, 'wb') as f:
                pickle.dump(cache_data, f)
            
            return result
        return wrapper
    return decorator

@app.route('/api/expensive-operation')
@disk_cache(expiration=1800)
def expensive_api_call():
    # Simulate expensive API call
    import time as t
    t.sleep(2)
    return jsonify({
        'result': 'Expensive computation result',
        'timestamp': time.time()
    })

@app.route('/api/data/<item_id>')
@disk_cache(expiration=600)
def get_data(item_id):
    # Simulate API call with parameters
    return jsonify({
        'item_id': item_id,
        'data': f'Data for item {item_id}',
        'fetched_at': time.time()
    })

def clear_cache():
    for filename in os.listdir(CACHE_DIR):
        if filename.endswith('.pkl'):
            os.remove(os.path.join(CACHE_DIR, filename))

def clear_expired_cache(expiration=DEFAULT_EXPIRATION):
    current_time = time.time()
    for filename in os.listdir(CACHE_DIR):
        if filename.endswith('.pkl'):
            cache_file = os.path.join(CACHE_DIR, filename)
            try:
                with open(cache_file, 'rb') as f:
                    cached_data = pickle.load(f)
                    if current_time - cached_data['timestamp'] > expiration:
                        os.remove(cache_file)
            except:
                os.remove(cache_file)

if __name__ == '__main__':
    app.run(debug=True)