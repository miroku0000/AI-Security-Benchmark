def cached(self, key_builder: Callable[..., str], ttl: Optional[int] = None):
        def decorator(func: Callable[..., Dict[str, Any]]):
            def wrapper(*args: Any, **kwargs: Any) -> Dict[str, Any]:
                key = key_builder(*args, **kwargs)
                cached_value = self.get(key)
                if cached_value is not None:
                    return cached_value