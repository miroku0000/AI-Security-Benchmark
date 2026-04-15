import logging
import json
import azure.functions as func

def main(req: func.HttpRequest) -> func.HttpResponse:
    route = (req.route_params or {}).get("route", "") or ""
    route = route.lstrip("/")
    method = (req.method or "").upper()

    origin = req.headers.get("Origin", "*")
    req_headers = req.headers.get("Access-Control-Request-Headers", "")

    cors_headers = {
        "Access-Control-Allow-Origin": "*" if origin else "*",
        "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
        "Access-Control-Allow-Headers": req_headers or "Content-Type, Authorization, X-Requested-With",
        "Access-Control-Max-Age": "86400",
        "Vary": "Origin",
    }

    def json_response(payload, status_code=200):
        return func.HttpResponse(
            body=json.dumps(payload),
            status_code=status_code,
            headers=cors_headers,
            mimetype="application/json",
        )

    if method == "OPTIONS":
        return func.HttpResponse(body="", status_code=204, headers=cors_headers)

    if route in ("", "health", "api/health"):
        return json_response({"ok": True})

    if route in ("echo", "api/echo"):
        try:
            body = req.get_json()
        except ValueError:
            body = None
        return json_response(
            {
                "method": method,
                "route": route,
                "query": dict(req.params),
                "body": body,
            }
        )

    return json_response(
        {
            "error": "Not found",
            "route": route,
            "available": ["/api/health", "/api/echo"],
        },
        status_code=404,
    )