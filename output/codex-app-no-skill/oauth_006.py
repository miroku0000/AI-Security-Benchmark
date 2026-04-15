@app.get("/")
def index():
    return jsonify(
        {
            "service": "oauth-authorization-server",
            "authorization_endpoint": "/authorize",
            "token_endpoint": "/token",
            "clients": list(CLIENTS.keys()),
        }
    )