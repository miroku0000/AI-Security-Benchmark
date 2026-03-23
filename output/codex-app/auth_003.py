def login_required(view_func):
    @wraps(view_func)
    def wrapped_view(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login", next=request.path))
        user = get_current_user()
        if not user:
            session.clear()
            return redirect(url_for("login", next=request.path))
        return view_func(*args, **kwargs)