@app.get("/")
def index():
    tenants = ", ".join(sorted(TENANT_CONFIGS.keys()))
    return f"Available tenants: {tenants}\nUse /login/<tenant> to start an OAuth 2.0 authorization flow.\n", 200