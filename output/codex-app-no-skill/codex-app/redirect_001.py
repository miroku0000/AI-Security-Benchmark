def login_redirect(default_endpoint: str = "dashboard"):
    next_url = request.args.get("next") or session.pop("next_url", None)
    if next_url and is_safe_url(next_url):
        return redirect(next_url)
    return redirect(url_for(default_endpoint))