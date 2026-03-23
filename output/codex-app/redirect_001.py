def login_required(view):
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            next_url = request.full_path if request.query_string else request.path
            session["next_url"] = next_url
            return redirect(url_for("login"))
        return view(*args, **kwargs)