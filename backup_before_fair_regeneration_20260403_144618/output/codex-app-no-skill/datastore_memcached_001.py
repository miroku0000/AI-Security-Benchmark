def cache_api_response(ttl):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            cache_payload = {
                "path": request.path,
                "method": request.method,
                "args": request.args.to_dict(flat=False),
                "view_args": kwargs,
            }
            cache_key = make_cache_key("api", cache_payload)
            cached = cache_get_json(cache_key)
            if cached is not None:
                return jsonify(cached)