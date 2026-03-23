def require_jwt(
    *,
    source_name: Optional[str] = None,
    audience: Optional[Union[str, Sequence[str]]] = None,
    g_key: str = "jwt_payload",
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def decorator(view: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(view)
        def wrapped(*args: Any, **kwargs: Any) -> Any:
            try:
                payload = current_jwt_verifier().verify_request(
                    source_name=source_name,
                    audience=audience,
                )
            except JWTVerificationError as exc:
                return jsonify({"error": "invalid_token", "message": str(exc)}), 401
            setattr(g, g_key, payload)
            return view(*args, **kwargs)