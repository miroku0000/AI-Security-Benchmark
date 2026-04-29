@app.before_request
def remember_destination():
    if request.endpoint in {"login", "static"}:
        return
    if "user_id" not in session and request.path.startswith("/protected"):
        session["next_url"] = request.full_path.rstrip("?")
        return redirect(url_for("login", next=request.full_path.rstrip("?")))