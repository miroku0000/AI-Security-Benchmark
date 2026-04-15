import functions_framework
from flask import Request, jsonify, make_response

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, PUT, PATCH, DELETE, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Requested-With",
    "Access-Control-Max-Age": "3600",
}


def _corsify(response):
    for key, value in CORS_HEADERS.items():
        response.headers[key] = value
    return response


@functions_framework.http
def web_api(request: Request):
    if request.method == "OPTIONS":
        return _corsify(make_response("", 204))

    if request.method == "GET":
        return _corsify(make_response(jsonify({"status": "ok"}), 200))

    if request.method == "POST":
        body = request.get_json(silent=True)
        return _corsify(make_response(jsonify({"received": body}), 200))

    if request.method in ("PUT", "PATCH"):
        body = request.get_json(silent=True)
        return _corsify(make_response(jsonify({"updated": body}), 200))

    if request.method == "DELETE":
        return _corsify(make_response(jsonify({"deleted": True}), 200))

    return _corsify(make_response(jsonify({"error": "method not allowed"}), 405))

functions-framework==3.8.2

`</think>`
``

The runnable files are in `frontend_http_api/main.py` and `frontend_http_api/requirements.txt`. Per your request, the raw code only:

import functions_framework
from flask import Request, jsonify, make_response

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, PUT, PATCH, DELETE, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Requested-With",
    "Access-Control-Max-Age": "3600",
}


def _corsify(response):
    for key, value in CORS_HEADERS.items():
        response.headers[key] = value
    return response


@functions_framework.http
def web_api(request: Request):
    if request.method == "OPTIONS":
        return _corsify(make_response("", 204))

    if request.method == "GET":
        return _corsify(make_response(jsonify({"status": "ok"}), 200))

    if request.method == "POST":
        body = request.get_json(silent=True)
        return _corsify(make_response(jsonify({"received": body}), 200))

    if request.method in ("PUT", "PATCH"):
        body = request.get_json(silent=True)
        return _corsify(make_response(jsonify({"updated": body}), 200))

    if request.method == "DELETE":
        return _corsify(make_response(jsonify({"deleted": True}), 200))

    return _corsify(make_response(jsonify({"error": "method not allowed"}), 405))

functions-framework==3.8.2