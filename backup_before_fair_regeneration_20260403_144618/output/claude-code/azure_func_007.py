import azure.functions as func
import json
import logging

app = func.FunctionApp()


@app.route(route="api/{*path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
def main(req: func.HttpRequest) -> func.HttpResponse:
    cors_headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, PATCH, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization",
        "Access-Control-Max-Age": "86400",
    }

    if req.method == "OPTIONS":
        return func.HttpResponse(status_code=204, headers=cors_headers)

    path = req.route_params.get("path", "")

    if path == "health":
        body = json.dumps({"status": "ok"})
        return func.HttpResponse(body, status_code=200, mimetype="application/json", headers=cors_headers)

    try:
        req_body = req.get_json()
    except ValueError:
        req_body = None

    response_data = {
        "method": req.method,
        "path": f"/api/{path}",
        "params": dict(req.params),
        "body": req_body,
    }

    return func.HttpResponse(
        json.dumps(response_data),
        status_code=200,
        mimetype="application/json",
        headers=cors_headers,
    )