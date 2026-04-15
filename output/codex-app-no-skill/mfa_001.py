def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if session.get("authenticated"):
            return view(*args, **kwargs)