def _method_not_allowed() -> Response:
    headers = {"Allow": ", ".join(ALLOWED_METHODS)}
    headers.update(_cors_headers())
    headers.update(_security_headers())
    return Response(
        response=json.dumps({"error": "method_not_allowed"}, separators=(",", ":"), sort_keys=True),
        status=405,
        headers=headers,
    )