def jwt_required(
    manager: JWTManager,
    *,
    source: Optional[str] = None,
    allowed_sources: Optional[Iterable[str]] = None,
    store_as: str = "jwt_payload",
) -> Callable[..., Any]:
    def decorator(view_func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(view_func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                payload = manager.verify_request(
                    request,
                    source=source,
                    allowed_sources=allowed_sources,
                )
            except JWTVerificationError as exc:
                raise Unauthorized(str(exc)) from exc