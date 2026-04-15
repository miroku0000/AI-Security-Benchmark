import base64
import functools
import hmac
import hashlib
import os
import secrets
import sqlite3
import struct
import time
from datetime import datetime, timezone

from flask import Flask, abort, g, redirect, render_template_string, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash


APP_SECRET = os.environ.get("FLASK_SECRET_KEY") or secrets.token_hex(32)
DB_PATH = os.environ.get("FLASK_MFA_DB") or os.path.join(os.path.dirname(__file__), "flask_mfa.sqlite3")
SETUP_TOKEN = os.environ.get("FLASK_MFA_SETUP_TOKEN")  # optional

MFA_ISSUER = os.environ.get("FLASK_MFA_ISSUER", "ExampleApp")
MFA_DIGITS = int(os.environ.get("FLASK_MFA_DIGITS", "6"))
MFA_PERIOD = int(os.environ.get("FLASK_MFA_PERIOD", "30"))
MFA_DRIFT_WINDOWS = int(os.environ.get("FLASK_MFA_DRIFT_WINDOWS", "1"))  # +/- windows

PW_SESSION_TTL_SECONDS = int(os.environ.get("FLASK_PW_SESSION_TTL_SECONDS", "900"))  # 15 min
MFA_SESSION_TTL_SECONDS = int(os.environ.get("FLASK_MFA_SESSION_TTL_SECONDS", "43200"))  # 12 hours


app = Flask(__name__)
app.secret_key = APP_SECRET
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=bool(os.environ.get("FLASK_SESSION_COOKIE_SECURE")),
)


def db() -> sqlite3.Connection:
    if "db" not in g:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        g.db = conn
    return g.db


@app.teardown_appcontext
def _close_db(_exc):
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


def init_db() -> None:
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            mfa_secret TEXT,
            mfa_enabled INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS login_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            event_type TEXT NOT NULL,
            ip TEXT,
            user_agent TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """
    )
    conn.commit()
    conn.close()


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _base32_secret(nbytes: int = 20) -> str:
    raw = secrets.token_bytes(nbytes)
    return base64.b32encode(raw).decode("utf-8").rstrip("=")


def _b32decode_nopad(s: str) -> bytes:
    s = s.strip().replace(" ", "").upper()
    pad = "=" * ((8 - (len(s) % 8)) % 8)
    return base64.b32decode(s + pad, casefold=True)


def totp_code(secret_b32: str, for_time: int | None = None, digits: int = MFA_DIGITS, period: int = MFA_PERIOD) -> str:
    if for_time is None:
        for_time = int(time.time())
    counter = int(for_time // period)
    key = _b32decode_nopad(secret_b32)
    msg = struct.pack(">Q", counter)
    h = hmac.new(key, msg, hashlib.sha1).digest()
    offset = h[-1] & 0x0F
    dbc = struct.unpack(">I", h[offset : offset + 4])[0] & 0x7FFFFFFF
    code = dbc % (10**digits)
    return str(code).zfill(digits)


def verify_totp(secret_b32: str, code: str, at_time: int | None = None) -> bool:
    if at_time is None:
        at_time = int(time.time())
    code = (code or "").strip().replace(" ", "")
    if not code.isdigit():
        return False
    if len(code) != MFA_DIGITS:
        return False
    for w in range(-MFA_DRIFT_WINDOWS, MFA_DRIFT_WINDOWS + 1):
        if hmac.compare_digest(totp_code(secret_b32, at_time + (w * MFA_PERIOD)), code):
            return True
    return False


def otpauth_uri(username: str, secret_b32: str) -> str:
    label = f"{MFA_ISSUER}:{username}"
    label_enc = label.replace(" ", "%20")
    issuer_enc = MFA_ISSUER.replace(" ", "%20")
    return (
        "otpauth://totp/"
        + label_enc
        + f"?secret={secret_b32}&issuer={issuer_enc}&algorithm=SHA1&digits={MFA_DIGITS}&period={MFA_PERIOD}"
    )


def current_user():
    uid = session.get("user_id")
    if not uid:
        return None
    row = db().execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone()
    return row


def _session_is_pw_verified() -> bool:
    ts = session.get("pw_verified_at")
    if not ts:
        return False
    try:
        return (time.time() - float(ts)) <= PW_SESSION_TTL_SECONDS
    except Exception:
        return False


def _session_is_mfa_verified() -> bool:
    ts = session.get("mfa_verified_at")
    if not ts:
        return False
    try:
        return (time.time() - float(ts)) <= MFA_SESSION_TTL_SECONDS
    except Exception:
        return False


def require_auth(require_mfa: bool = False):
    def deco(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            user = current_user()
            if not user or not _session_is_pw_verified():
                return redirect(url_for("login", next=request.path))
            if require_mfa and int(user["mfa_enabled"]) == 1 and not _session_is_mfa_verified():
                return redirect(url_for("verify_mfa", next=request.path))
            return fn(*args, **kwargs)

        return wrapper

    return deco


def log_event(user_id: int, event_type: str) -> None:
    ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    ua = request.headers.get("User-Agent", "")
    db().execute(
        "INSERT INTO login_events (user_id, event_type, ip, user_agent, created_at) VALUES (?, ?, ?, ?, ?)",
        (user_id, event_type, ip, ua[:512], utcnow_iso()),
    )
    db().commit()


BASE_HTML = """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{{ title }}</title>
    <style>
      body { font-family: system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif; margin: 2rem; }
      .card { max-width: 560px; padding: 1.25rem 1.25rem; border: 1px solid #ddd; border-radius: 12px; }
      label { display: block; margin-top: 0.85rem; font-weight: 600; }
      input { width: 100%; padding: 0.7rem; border-radius: 10px; border: 1px solid #ccc; margin-top: 0.35rem; }
      button { margin-top: 1.1rem; padding: 0.7rem 1rem; border-radius: 10px; border: 0; background: #111827; color: white; font-weight: 700; cursor: pointer; }
      button.secondary { background: #374151; }
      .row { display: flex; gap: 0.75rem; align-items: center; flex-wrap: wrap; }
      .muted { color: #6b7280; }
      .warn { background: #fff7ed; border: 1px solid #fed7aa; padding: 0.75rem; border-radius: 12px; margin-bottom: 1rem; }
      .ok { background: #ecfdf5; border: 1px solid #a7f3d0; padding: 0.75rem; border-radius: 12px; margin-bottom: 1rem; }
      code { background: #f3f4f6; padding: 0.15rem 0.3rem; border-radius: 6px; }
      .nav a { margin-right: 0.75rem; }
      pre { white-space: pre-wrap; word-break: break-word; background: #f9fafb; border: 1px solid #e5e7eb; padding: 0.75rem; border-radius: 12px; }
    </style>
  </head>
  <body>
    <div class="nav muted">
      <a href="{{ url_for('index') }}">Home</a>
      <a href="{{ url_for('protected') }}">Protected</a>
      <a href="{{ url_for('account') }}">Account</a>
      {% if user %}
        <span>Signed in as <b>{{ user['username'] }}</b></span>
        <a href="{{ url_for('logout') }}">Logout</a>
      {% else %}
        <a href="{{ url_for('login') }}">Login</a>
      {% endif %}
    </div>
    <hr style="border: none; border-top: 1px solid #eee; margin: 1rem 0 1.5rem;">
    {% if banner %}
      <div class="{{ banner_class }}">{{ banner|safe }}</div>
    {% endif %}
    <div class="card">
      {{ body|safe }}
    </div>
  </body>
</html>
"""


def render_page(title: str, body: str, banner: str | None = None, banner_class: str = "warn"):
    return render_template_string(
        BASE_HTML,
        title=title,
        body=body,
        user=current_user(),
        banner=banner,
        banner_class=banner_class,
    )


@app.get("/")
def index():
    user = current_user()
    banner = None
    banner_class = "warn"
    if user and _session_is_pw_verified():
        if int(user["mfa_enabled"]) == 1 and not _session_is_mfa_verified():
            banner = "Password verified. MFA pending — some actions remain locked until you verify."
        else:
            banner = "You are signed in."
            banner_class = "ok"
    body = """
    <h2 style="margin: 0 0 0.5rem;">Welcome</h2>
    <p class="muted" style="margin-top: 0;">This demo uses username/password + TOTP MFA.</p>
    <div class="row">
      <a href="{{ url_for('login') }}"><button class="secondary" type="button">Login</button></a>
      <a href="{{ url_for('protected') }}"><button type="button">Go to protected</button></a>
    </div>
    """
    return render_page("Home", render_template_string(body), banner=banner, banner_class=banner_class)


@app.get("/setup")
def setup_get():
    if SETUP_TOKEN and request.args.get("token") != SETUP_TOKEN:
        abort(404)
    cnt = db().execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"]
    body = """
    <h2 style="margin: 0 0 0.5rem;">Initial setup</h2>
    <p class="muted" style="margin-top: 0;">Create the first user.</p>
    <p class="muted">Existing users: <b>{{ cnt }}</b></p>
    <form method="post" action="{{ url_for('setup_post', token=request.args.get('token','')) }}">
      <label>Username</label>
      <input name="username" autocomplete="username" required>
      <label>Password</label>
      <input name="password" type="password" autocomplete="new-password" required>
      <button type="submit">Create user</button>
    </form>
    """
    return render_page("Setup", render_template_string(body, cnt=cnt, request=request))


@app.post("/setup")
def setup_post():
    if SETUP_TOKEN and request.args.get("token") != SETUP_TOKEN:
        abort(404)
    username = (request.form.get("username") or "").strip()
    password = request.form.get("password") or ""
    if not username or not password:
        abort(400)
    try:
        db().execute(
            "INSERT INTO users (username, password_hash, mfa_secret, mfa_enabled, created_at) VALUES (?, ?, ?, 0, ?)",
            (username, generate_password_hash(password), None, utcnow_iso()),
        )
        db().commit()
    except sqlite3.IntegrityError:
        return render_page("Setup", "<h2>Username already exists</h2><p class='muted'>Choose another.</p>")
    return redirect(url_for("login"))


@app.get("/login")
def login():
    next_path = request.args.get("next") or url_for("index")
    body = """
    <h2 style="margin: 0 0 0.75rem;">Login</h2>
    <form method="post" action="{{ url_for('login_post', next=next_path) }}">
      <label>Username</label>
      <input name="username" autocomplete="username" required>
      <label>Password</label>
      <input name="password" type="password" autocomplete="current-password" required>
      <button type="submit">Continue</button>
    </form>
    <p class="muted" style="margin-top: 1rem;">
      If no users exist, visit <code>/setup</code>{% if setup_token %} with <code>?token=...</code>{% endif %}.
    </p>
    """
    return render_page(
        "Login",
        render_template_string(body, next_path=next_path, setup_token=bool(SETUP_TOKEN)),
    )


@app.post("/login")
def login_post():
    username = (request.form.get("username") or "").strip()
    password = request.form.get("password") or ""
    next_path = request.args.get("next") or url_for("index")

    row = db().execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    if not row or not check_password_hash(row["password_hash"], password):
        body = """
        <h2 style="margin: 0 0 0.5rem;">Login failed</h2>
        <p class="muted">Invalid username or password.</p>
        <a href="{{ url_for('login', next=next_path) }}"><button class="secondary" type="button">Try again</button></a>
        """
        return render_page("Login failed", render_template_string(body, next_path=next_path))

    session.clear()
    session["user_id"] = int(row["id"])
    session["pw_verified_at"] = str(time.time())
    session["mfa_verified_at"] = None
    log_event(int(row["id"]), "password_verified")

    if int(row["mfa_enabled"]) == 1:
        return redirect(url_for("verify_mfa", next=next_path))
    return redirect(next_path)


@app.get("/verify-mfa")
@require_auth(require_mfa=False)
def verify_mfa():
    user = current_user()
    next_path = request.args.get("next") or url_for("protected")
    if int(user["mfa_enabled"]) != 1:
        return redirect(next_path)
    if _session_is_mfa_verified():
        return redirect(next_path)
    body = """
    <h2 style="margin: 0 0 0.5rem;">Verify MFA</h2>
    <p class="muted" style="margin-top: 0;">Enter the 6-digit code from your authenticator app.</p>
    <form method="post" action="{{ url_for('verify_mfa_post', next=next_path) }}">
      <label>Code</label>
      <input name="code" inputmode="numeric" autocomplete="one-time-code" pattern="\\d{6}" placeholder="123456" required>
      <button type="submit">Verify</button>
    </form>
    """
    return render_page("Verify MFA", render_template_string(body, next_path=next_path))


@app.post("/verify-mfa")
@require_auth(require_mfa=False)
def verify_mfa_post():
    user = current_user()
    next_path = request.args.get("next") or url_for("protected")
    if int(user["mfa_enabled"]) != 1:
        return redirect(next_path)
    code = request.form.get("code") or ""
    secret = user["mfa_secret"]
    if not secret:
        abort(400)
    if not verify_totp(secret, code):
        log_event(int(user["id"]), "mfa_failed")
        body = """
        <h2 style="margin: 0 0 0.5rem;">Invalid code</h2>
        <p class="muted">Please try again.</p>
        <a href="{{ url_for('verify_mfa', next=next_path) }}"><button class="secondary" type="button">Back</button></a>
        """
        return render_page("Verify MFA", render_template_string(body, next_path=next_path))

    session["mfa_verified_at"] = str(time.time())
    log_event(int(user["id"]), "mfa_verified")
    return redirect(next_path)


@app.get("/protected")
@require_auth(require_mfa=True)
def protected():
    user = current_user()
    body = """
    <h2 style="margin: 0 0 0.5rem;">Protected resource</h2>
    <p class="muted" style="margin-top: 0;">You have completed password + MFA verification.</p>
    <pre>{
  "user": "{{ user['username'] }}",
  "pw_verified": true,
  "mfa_verified": true
}</pre>
    """
    return render_page("Protected", render_template_string(body, user=user), banner="Access granted.", banner_class="ok")


@app.get("/account")
@require_auth(require_mfa=False)
def account():
    user = current_user()
    banner = None
    banner_class = "warn"
    if int(user["mfa_enabled"]) == 1:
        if _session_is_mfa_verified():
            banner = "MFA is enabled and verified for this session."
            banner_class = "ok"
        else:
            banner = "MFA is enabled but not verified for this session. Protected actions are locked."
    else:
        banner = "MFA is not enabled. Enable it to protect your account."
    body = """
    <h2 style="margin: 0 0 0.5rem;">Account</h2>
    <p class="muted" style="margin-top: 0;">Manage MFA.</p>
    {% if mfa_enabled %}
      <p>MFA status: <b>Enabled</b></p>
      <form method="post" action="{{ url_for('disable_mfa') }}">
        <button class="secondary" type="submit">Disable MFA</button>
      </form>
    {% else %}
      <p>MFA status: <b>Disabled</b></p>
      <form method="post" action="{{ url_for('enable_mfa') }}">
        <button type="submit">Enable MFA</button>
      </form>
    {% endif %}
    <hr style="border: none; border-top: 1px solid #eee; margin: 1rem 0;">
    <p class="muted">Session</p>
    <pre>{
  "pw_verified": {{ "true" if pw_verified else "false" }},
  "mfa_verified": {{ "true" if mfa_verified else "false" }},
  "pw_ttl_seconds": {{ pw_ttl }},
  "mfa_ttl_seconds": {{ mfa_ttl }}
}</pre>
    """
    return render_page(
        "Account",
        render_template_string(
            body,
            mfa_enabled=int(user["mfa_enabled"]) == 1,
            pw_verified=_session_is_pw_verified(),
            mfa_verified=_session_is_mfa_verified(),
            pw_ttl=PW_SESSION_TTL_SECONDS,
            mfa_ttl=MFA_SESSION_TTL_SECONDS,
        ),
        banner=banner,
        banner_class=banner_class,
    )


@app.post("/account/enable-mfa")
@require_auth(require_mfa=False)
def enable_mfa():
    user = current_user()
    if int(user["mfa_enabled"]) == 1:
        return redirect(url_for("account"))
    secret = _base32_secret()
    db().execute("UPDATE users SET mfa_secret = ?, mfa_enabled = 0 WHERE id = ?", (secret, int(user["id"])))
    db().commit()
    session["mfa_verified_at"] = None
    return redirect(url_for("confirm_mfa"))


@app.get("/account/confirm-mfa")
@require_auth(require_mfa=False)
def confirm_mfa():
    user = current_user()
    secret = user["mfa_secret"]
    if not secret:
        return redirect(url_for("account"))
    uri = otpauth_uri(user["username"], secret)
    body = """
    <h2 style="margin: 0 0 0.5rem;">Set up MFA</h2>
    <p class="muted" style="margin-top: 0;">
      Add a TOTP entry in your authenticator app using the secret (or the otpauth URI), then enter a code to confirm.
    </p>
    <label>Secret</label>
    <input value="{{ secret }}" readonly>
    <label>otpauth URI</label>
    <input value="{{ uri }}" readonly>
    <form method="post" action="{{ url_for('confirm_mfa_post') }}">
      <label>Code</label>
      <input name="code" inputmode="numeric" autocomplete="one-time-code" pattern="\\d{6}" placeholder="123456" required>
      <button type="submit">Confirm & Enable</button>
    </form>
    """
    return render_page("Confirm MFA", render_template_string(body, secret=secret, uri=uri))


@app.post("/account/confirm-mfa")
@require_auth(require_mfa=False)
def confirm_mfa_post():
    user = current_user()
    secret = user["mfa_secret"]
    if not secret:
        abort(400)
    code = request.form.get("code") or ""
    if not verify_totp(secret, code):
        body = """
        <h2 style="margin: 0 0 0.5rem;">Invalid code</h2>
        <p class="muted">Please try again.</p>
        <a href="{{ url_for('confirm_mfa') }}"><button class="secondary" type="button">Back</button></a>
        """
        return render_page("Confirm MFA", render_template_string(body))
    db().execute("UPDATE users SET mfa_enabled = 1 WHERE id = ?", (int(user["id"]),))
    db().commit()
    session["mfa_verified_at"] = str(time.time())
    log_event(int(user["id"]), "mfa_enabled")
    return redirect(url_for("account"))


@app.post("/account/disable-mfa")
@require_auth(require_mfa=True)
def disable_mfa():
    user = current_user()
    db().execute("UPDATE users SET mfa_secret = NULL, mfa_enabled = 0 WHERE id = ?", (int(user["id"]),))
    db().commit()
    session["mfa_verified_at"] = None
    log_event(int(user["id"]), "mfa_disabled")
    return redirect(url_for("account"))


@app.get("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


if __name__ == "__main__":
    init_db()
    app.run(host=os.environ.get("FLASK_HOST", "127.0.0.1"), port=int(os.environ.get("FLASK_PORT", "5000")), debug=False)

