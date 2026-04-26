import os
from datetime import datetime, timezone
from typing import Any

from flask import Flask, jsonify, make_response, request


APP_NAME = os.environ.get("APP_NAME", "frontend-api")
APP_ENV = os.environ.get("APP_ENV", "development")
PORT = int(os.environ.get("PORT", "8080"))

app = Flask(__name__)


def _cors_headers() -> dict[str, str]:
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization",
        "Access-Control-Max-Age": "3600",
    }


def _json_response(payload: dict[str, Any], status_code: int = 200):
    response = make_response(jsonify(payload), status_code)
    for header_name, header_value in _cors_headers().items():
        response.headers[header_name] = header_value
    return response


def _preflight_response():
    response = make_response("", 204)
    for header_name, header_value in _cors_headers().items():
        response.headers[header_name] = header_value
    return response


def frontend_api(request):
    if request.method == "OPTIONS":
        return _preflight_response()

    path = request.path.rstrip("/") or "/"

    if path == "/":
        return _json_response(
            {
                "name": APP_NAME,
                "environment": APP_ENV,
                "message": "Cloud Function HTTP API is running.",
                "routes": {
                    "GET /": "API metadata",
                    "GET /health": "Health check",
                    "POST /echo": "Echo request JSON",
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

    if path == "/health":
        return _json_response(
            {
                "status": "ok",
                "service": APP_NAME,
                "environment": APP_ENV,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

    if path == "/echo" and request.method == "POST":
        payload = request.get_json(silent=True)
        if payload is None:
            return _json_response({"error": "Request body must be valid JSON."}, 400)

        return _json_response(
            {
                "received": payload,
                "method": request.method,
                "path": path,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

    return _json_response(
        {
            "error": "Not found",
            "method": request.method,
            "path": path,
        },
        404,
    )


@app.route("/", defaults={"route_path": ""}, methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])
@app.route("/<path:route_path>", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])
def local_entrypoint(route_path: str):
    return frontend_api(request)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)