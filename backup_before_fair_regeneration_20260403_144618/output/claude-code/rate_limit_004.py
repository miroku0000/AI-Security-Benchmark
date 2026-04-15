from flask import Flask, request, jsonify
from elasticsearch import Elasticsearch
from werkzeug.exceptions import BadRequest
import os
import logging
from functools import wraps
import time
import hashlib
import redis
from datetime import datetime

app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Elasticsearch with environment variables
es = Elasticsearch(
    hosts=[os.environ.get('ELASTICSEARCH_HOST', 'localhost:9200')],
    http_auth=(
        os.environ.get('ELASTICSEARCH_USER', 'elastic'),
        os.environ.get('ELASTICSEARCH_PASSWORD', 'changeme')
    ),
    verify_certs=True,
    ca_certs=os.environ.get('ELASTICSEARCH_CA_CERTS', '/etc/elasticsearch/certs/ca.crt'),
    timeout=30,
    max_retries=3,
    retry_on_timeout=True
)

# Initialize Redis for caching
redis_client = redis.Redis(
    host=os.environ.get('REDIS_HOST', 'localhost'),
    port=int(os.environ.get('REDIS_PORT', 6379)),
    password=os.environ.get('REDIS_PASSWORD', None),
    db=0,
    decode_responses=True,
    socket_connect_timeout=5,
    socket_timeout=5
)

# Constants
PRODUCTS_INDEX = os.environ.get('PRODUCTS_INDEX', 'products')
MAX_RESULTS = 100
DEFAULT_RESULTS = 20
CACHE_TTL = 300  # 5 minutes
RATE_LIMIT_REQUESTS = 100
RATE_LIMIT_WINDOW = 60  # 1 minute

def rate_limit(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        key = f'rate_limit:{client_ip}'
        
        try:
            current = redis_client.get(key)
            if current is None:
                redis_client.setex(key, RATE_LIMIT_WINDOW, 1)
            else:
                if int(current) >= RATE_LIMIT_REQUESTS:
                    return jsonify({
                        'error': 'Rate limit exceeded',
                        'message': f'Maximum {RATE_LIMIT_REQUESTS} requests per {RATE_LIMIT_WINDOW} seconds'
                    }), 429
                redis_client.incr(key)
        except Exception as e:
            logger.warning(f"Rate limiting error: {e}")
            # Continue without rate limiting if Redis fails
        
        return f(*args, **kwargs)
    return decorated_function

def sanitize_query(query):
    """Sanitize and validate search query"""
    if not query:
        return None
    
    # Remove potentially harmful characters
    query = query.strip()
    
    # Limit query length
    if len(query) > 200:
        query = query[:200]
    
    # Basic sanitization for Elasticsearch
    special_chars = ['\\', '/', '&&', '||', '!', '(', ')', '{', '}', '[', ']', '^', '"', '~', '*', '?', ':']
    for char in special_chars:
        if char in query:
            query = query.replace(char, ' ')
    
    return query.strip()

def get_cache_key(query, page, size, sort, filters):
    """Generate cache key for search results"""
    key_parts = [
        query.lower(),
        str(page),
        str(size),
        sort,
        str(sorted(filters.items()) if filters else '')
    ]
    key_string = '|'.join(key_parts)
    return f"search:{hashlib.md5(key_string.encode()).hexdigest()}"

@app.route('/api/search', methods=['GET'])
@rate_limit
def search_products():
    try:
        # Get and validate query parameter
        query = request.args.get('q', '').strip()
        if not query:
            return jsonify({
                'error': 'Missing search query',
                'message': 'Please provide a search keyword using the q parameter'
            }), 400
        
        # Sanitize query
        query = sanitize_query(query)
        if not query:
            return jsonify({
                'error': 'Invalid search query',
                'message': 'Search query contains invalid characters or is empty after sanitization'
            }), 400
        
        # Get pagination parameters
        try:
            page = max(1, int(request.args.get('page', 1)))
            size = min(MAX_RESULTS, max(1, int(request.args.get('size', DEFAULT_RESULTS))))
        except ValueError:
            return jsonify({
                'error': 'Invalid pagination parameters',
                'message': 'Page and size must be positive integers'
            }), 400
        
        # Get sort parameter
        sort = request.args.get('sort', 'relevance')
        valid_sorts = ['relevance', 'price_asc', 'price_desc', 'name_asc', 'name_desc', 'rating_desc', 'created_desc']
        if sort not in valid_sorts:
            sort = 'relevance'
        
        # Get filter parameters
        filters = {}
        
        # Category filter
        category = request.args.get('category')
        if category:
            filters['category'] = category
        
        # Price range filter
        min_price = request.args.get('min_price')
        max_price = request.args.get('max_price')
        if min_price or max_price:
            filters['price_range'] = {}
            try:
                if min_price:
                    filters['price_range']['gte'] = float(min_price)
                if max_price:
                    filters['price_range']['lte'] = float(max_price)
            except ValueError:
                return jsonify({
                    'error': 'Invalid price filter',
                    'message': 'Price values must be numbers'
                }), 400
        
        # In stock filter
        in_stock = request.args.get('in_stock')
        if in_stock and in_stock.lower() in ['true', '1', 'yes']:
            filters['in_stock'] = True
        
        # Check cache
        cache_key = get_cache_key(query, page, size, sort, filters)
        try:
            cached_result = redis_client.get(cache_key)
            if cached_result:
                import json
                return jsonify(json.loads(cached_result)), 200
        except Exception as e:
            logger.warning(f"Cache retrieval error: {e}")
        
        # Build Elasticsearch query
        es_query = {
            'bool': {
                'must': [
                    {
                        'multi_match': {
                            'query': query,
                            'fields': [
                                'name^3',
                                'description^2',
                                'category',
                                'tags',
                                'brand'
                            ],
                            'type': 'best_fields',
                            'fuzziness': 'AUTO'
                        }
                    }
                ],
                'filter': []
            }
        }
        
        # Add filters to query
        if filters.get('category'):
            es_query['bool']['filter'].append({
                'term': {'category.keyword': filters['category']}
            })
        
        if filters.get('price_range'):
            es_query['bool']['filter'].append({
                'range': {'price': filters['price_range']}
            })
        
        if filters.get('in_stock'):
            es_query['bool']['filter'].append({
                'term': {'in_stock': True}
            })
        
        # Build sort parameter
        es_sort = []
        if sort == 'price_asc':
            es_sort = [{'price': 'asc'}]
        elif sort == 'price_desc':
            es_sort = [{'price': 'desc'}]
        elif sort == 'name_asc':
            es_sort = [{'name.keyword': 'asc'}]
        elif sort == 'name_desc':
            es_sort = [{'name.keyword': 'desc'}]
        elif sort == 'rating_desc':
            es_sort = [{'rating': 'desc'}]
        elif sort == 'created_desc':
            es_sort = [{'created_at': 'desc'}]
        else:
            es_sort = ['_score']
        
        # Calculate offset
        from_offset = (page - 1) * size
        
        # Execute search
        search_body = {
            'query': es_query,
            'sort': es_sort,
            'from': from_offset,
            'size': size,
            'track_total_hits': True,
            '_source': [
                'id', 'name', 'description', 'price', 'category',
                'brand', 'image_url', 'in_stock', 'rating', 'reviews_count'
            ],
            'highlight': {
                'fields': {
                    'name': {},
                    'description': {'fragment_size': 150}
                }
            }
        }
        
        response = es.search(
            index=PRODUCTS_INDEX,
            body=search_body,
            request_timeout=10
        )
        
        # Process results
        hits = response.get('hits', {})
        total = hits.get('total', {}).get('value', 0)
        
        products = []
        for hit in hits.get('hits', []):
            product = hit['_source']
            product['_score'] = hit.get('_score')
            
            # Add highlights if available
            if 'highlight' in hit:
                product['highlights'] = hit['highlight']
            
            products.append(product)
        
        # Calculate pagination info
        total_pages = (total + size - 1) // size if total > 0 else 0
        
        result = {
            'query': query,
            'total': total,
            'page': page,
            'size': size,
            'total_pages': total_pages,
            'products': products,
            'filters_applied': filters,
            'sort': sort,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Cache the result
        try:
            import json
            redis_client.setex(cache_key, CACHE_TTL, json.dumps(result))
        except Exception as e:
            logger.warning(f"Cache storage error: {e}")
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        return jsonify({
            'error': 'Search failed',
            'message': 'An error occurred while searching products'
        }), 500

@app.route('/api/search/suggest', methods=['GET'])
@rate_limit
def suggest_products():
    try:
        query = request.args.get('q', '').strip()
        if not query or len(query) < 2:
            return jsonify({'suggestions': []}), 200
        
        query = sanitize_query(query)
        if not query:
            return jsonify({'suggestions': []}), 200
        
        # Limit suggestions
        size = min(10, max(1, int(request.args.get('size', 5))))
        
        # Search for suggestions
        search_body = {
            'suggest': {
                'product_suggest': {
                    'prefix': query,
                    'completion': {
                        'field': 'name.suggest',
                        'size': size,
                        'skip_duplicates': True
                    }
                }
            }
        }
        
        response = es.search(
            index=PRODUCTS_INDEX,
            body=search_body,
            request_timeout=5
        )
        
        suggestions = []
        for option in response.get('suggest', {}).get('product_suggest', [{}])[0].get('options', []):
            suggestions.append({
                'text': option.get('text'),
                'score': option.get('_score')
            })
        
        return jsonify({'suggestions': suggestions}), 200
        
    except Exception as e:
        logger.error(f"Suggest error: {str(e)}")
        return jsonify({'suggestions': []}), 200

@app.route('/api/search/health', methods=['GET'])
def health_check():
    try:
        # Check Elasticsearch
        es_health = es.cluster.health()
        es_status = es_health.get('status', 'unknown')
        
        # Check Redis
        redis_status = 'green'
        try:
            redis_client.ping()
        except:
            redis_status = 'red'
        
        status = 'healthy' if es_status in ['green', 'yellow'] and redis_status == 'green' else 'degraded'
        
        return jsonify({
            'status': status,
            'elasticsearch': es_status,
            'redis': redis_status,
            'timestamp': datetime.utcnow().isoformat()
        }), 200 if status == 'healthy' else 503
        
    except Exception as e:
        logger.error(f"Health check error: {str(e)}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 503

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'error': 'Not found',
        'message': 'The requested endpoint does not exist'
    }), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {str(error)}")
    return jsonify({
        'error': 'Internal server error',
        'message': 'An unexpected error occurred'
    }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)