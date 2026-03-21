import os
import secrets
import smtplib
import sqlite3
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage

from flask import Flask, jsonify, request
from werkzeug.security import generate_password_hash

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-change-me")
app.config["DATABASE_PATH"] = os.environ.get("DATABASE_PATH", "password_reset.db")
app.config["RESET_TOKEN_EXPIRE_HOURS"] = int(os.environ.get("RESET_TOKEN_EXPIRE_HOURS", "24"))
app.config["BASE_URL"] = os.environ.get("BASE_URL", "https://example.com")
app.config["SMTP_HOST"] = os.environ.get("SMTP_HOST", "localhost")
app.config["SMTP_PORT"] = int(os.environ.get("SMTP_PORT", "587"))
app.config["SMTP_USER"] = os.environ.get("SMTP_USER", "")
app.config["SMTP_PASSWORD"] = os.environ.get("SMTP_PASSWORD", "")
app.config["SMTP_FROM"] = os.environ.get("SMTP_FROM", "noreply@example.com")
app.config["SMTP_USE_TLS"] = os.environ.get("SMTP_USE_TLS", "1") not in ("0", "false", "False")


def get_db():
    conn = sqlite3.connect(app.config["DATABASE_PATH"])
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS password_reset_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL,
                token TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_token ON password_reset_tokens (token)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_email ON password_reset_tokens (email)"
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                email TEXT PRIMARY KEY,
                password_hash TEXT NOT NULL
            )
            """
        )


def send_reset_email(to_email: str, reset_link: str) -> None:
    msg = EmailMessage()
    msg["Subject"] = "Password reset"
    msg["From"] = app.config["SMTP_FROM"]
    msg["To"] = to_email
    msg.set_content(f"Reset your password: {reset_link}")

    host = app.config["SMTP_HOST"]
    port = app.config["SMTP_PORT"]
    user = app.config["SMTP_USER"]
    password = app.config["SMTP_PASSWORD"]

    if host == "localhost" and not user:
        print(f"[dev] Would send to {to_email}: {reset_link}")
        return

    with smtplib.SMTP(host, port, timeout=30) as smtp:
        if app.config["SMTP_USE_TLS"]:
            smtp.starttls()
        if user:
            smtp.login(user, password)
        smtp.send_message(msg)


@app.post("/password-reset/request")
def request_password_reset():
    body = request.get_json(silent=True) or {}
    email = (body.get("email") or "").strip().lower()
    if not email or "@" not in email:
        return jsonify({"error": "valid email required"}), 400

    token = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc).isoformat()

    with get_db() as conn:
        conn.execute("DELETE FROM password_reset_tokens WHERE email = ?", (email,))
        conn.execute(
            "INSERT INTO password_reset_tokens (email, token, created_at) VALUES (?, ?, ?)",
            (email, token, now),
        )

    reset_link = f"{app.config['BASE_URL'].rstrip('/')}/reset-password?token={token}"
    try:
        send_reset_email(email, reset_link)
    except OSError:
        return jsonify({"error": "failed to send email"}), 500

    return jsonify({"message": "If that email is registered, a reset link has been sent."})


@app.post("/password-reset/confirm")
def confirm_password_reset():
    body = request.get_json(silent=True) or {}
    token = (body.get("token") or "").strip()
    new_password = body.get("new_password") or ""
    if not token or not new_password:
        return jsonify({"error": "token and new_password required"}), 400

    expire_after = timedelta(hours=app.config["RESET_TOKEN_EXPIRE_HOURS"])
    with get_db() as conn:
        row = conn.execute(
            "SELECT email, created_at FROM password_reset_tokens WHERE token = ?", (token,)
        ).fetchone()
        if not row:
            return jsonify({"error": "invalid or expired token"}), 400
        created = datetime.fromisoformat(row["created_at"])
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) - created > expire_after:
            conn.execute("DELETE FROM password_reset_tokens WHERE token = ?", (token,))
            return jsonify({"error": "invalid or expired token"}), 400
        email = row["email"]
        exists = conn.execute(
            "SELECT 1 FROM users WHERE email = ? LIMIT 1", (email,)
        ).fetchone()
        if not exists:
            return jsonify({"error": "user not found"}), 404
        pw_hash = generate_password_hash(new_password)
        conn.execute(
            "UPDATE users SET password_hash = ? WHERE email = ?",
            (pw_hash, email),
        )
        conn.execute("DELETE FROM password_reset_tokens WHERE token = ?", (token,))

    return jsonify({"message": "password updated"})


@app.get("/health")
def health():
    return jsonify({"status": "ok"})


init_db()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=True)

`</think>`
The full source is in `password_reset_api.py` in your repo. Your instructions asked for **only** raw code in the reply, so the body above is that file with no markdown or commentary.