import json
from typing import Any

import azure.functions as func

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)


def _cors_headers() -> dict[str, str]:
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, PUT, PATCH, DELETE, OPTIONS",
        "Access-Control-Allow-Headers": "*",
        "Access-Control-Max-Age": "86400",
        "Content-Type": "application/json",
    }


def _json_response(payload: Any, status_code: int = 200) -> func.HttpResponse:
    return func.HttpResponse(
        body=json.dumps(payload),
        status_code=status_code,
        headers=_cors_headers(),
        mimetype="application/json",
    )


@app.route(route="health", methods=["GET"])
def health(req: func.HttpRequest) -> func.HttpResponse:
    return _json_response(
        {
            "status": "ok",
            "service": "spa-http-api",
            "method": req.method,
        }
    )


@app.route(route="messages", methods=["GET", "POST"])
def messages(req: func.HttpRequest) -> func.HttpResponse:
    if req.method == "GET":
        return _json_response(
            {
                "items": [
                    {"id": 1, "text": "Hello from Azure Functions"},
                    {"id": 2, "text": "CORS is enabled for all origins"},
                ]
            }
        )

    try:
        payload = req.get_json()
    except ValueError:
        payload = {"raw": req.get_body().decode("utf-8", errors="replace")}

    return _json_response(
        {
            "received": payload,
            "message": "Request processed successfully",
        },
        status_code=201,
    )


@app.route(route="{*path}", methods=["OPTIONS"])
def options_preflight(req: func.HttpRequest) -> func.HttpResponse:
    return func.HttpResponse(status_code=204, headers=_cors_headers())
PY

cat > azure_spa_http_api/host.json <<'JSON'
{
  "version": "2.0",
  "extensionBundle": {
    "id": "Microsoft.Azure.Functions.ExtensionBundle",
    "version": "[4.*, 5.0.0)"
  },
  "extensions": {
    "http": {
      "routePrefix": "api"
    }
  }
}
JSON

cat > azure_spa_http_api/local.settings.json <<'JSON'
{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsStorage": "UseDevelopmentStorage=true",
    "FUNCTIONS_WORKER_RUNTIME": "python"
  },
  "Host": {
    "CORS": "*",
    "CORSCredentials": false
  }
}
JSON

cat > azure_spa_http_api/requirements.txt <<'TXT'
azure-functions>=1.20.0
TXT