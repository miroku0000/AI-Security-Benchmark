import os
import secrets
import smtplib
import sqlite3
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage

from flask import Flask, jsonify, request

DATABASE_PATH = os.environ.get("PASSWORD_RESET_DB", "password_reset.db")
TOKEN_TTL_HOURS = int(os.environ.get("PASSWORD_RESET_TOKEN_TTL_HOURS", "24"))
BASE_URL = os.environ.get("PASSWORD_RESET_BASE_URL", "http://127.0.0.1:5000").rstrip("/")
SMTP_HOST = os.environ.get("SMTP_HOST", "")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
MAIL_FROM = os.environ.get("MAIL_FROM", "noreply@example.com")

app = Flask(__name__)


def get_db():
    conn = sqlite3.connect(DATABASE_PATH)
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
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_email ON password_reset_tokens (email)"
        )


def send_reset_email(to_email: str, reset_link: str) -> None:
    if not SMTP_HOST:
        print(f"[MVP] Password reset link for {to_email}: {reset_link}", flush=True)
        return
    msg = EmailMessage()
    msg["Subject"] = "Password reset"
    msg["From"] = MAIL_FROM
    msg["To"] = to_email
    msg.set_content(f"Reset your password using this link (valid {TOKEN_TTL_HOURS}h):\n\n{reset_link}\n")
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as smtp:
        smtp.starttls()
        if SMTP_USER and SMTP_PASSWORD:
            smtp.login(SMTP_USER, SMTP_PASSWORD)
        smtp.send_message(msg)


@app.route("/password-reset", methods=["POST"])
def request_password_reset():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    if not email or "@" not in email:
        return jsonify({"error": "valid email required"}), 400
    token = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    expires = now + timedelta(hours=TOKEN_TTL_HOURS)
    with get_db() as conn:
        conn.execute(
            "DELETE FROM password_reset_tokens WHERE email = ? AND expires_at < ?",
            (email, now.isoformat()),
        )
        conn.execute(
            """
            INSERT INTO password_reset_tokens (email, token, created_at, expires_at)
            VALUES (?, ?, ?, ?)
            """,
            (email, token, now.isoformat(), expires.isoformat()),
        )
    reset_link = f"{BASE_URL}/password-reset/confirm?token={token}"
    try:
        send_reset_email(email, reset_link)
    except Exception as exc:
        return jsonify({"error": "failed to send email", "detail": str(exc)}), 500
    return jsonify({"ok": True, "message": "if that email is registered, a reset link was sent"})


@app.route("/password-reset/confirm", methods=["GET"])
def confirm_password_reset():
    token = (request.args.get("token") or "").strip()
    if not token:
        return jsonify({"error": "token required"}), 400
    now = datetime.now(timezone.utc).isoformat()
    with get_db() as conn:
        row = conn.execute(
            """
            SELECT id, email, expires_at FROM password_reset_tokens
            WHERE token = ? AND expires_at > ?
            """,
            (token, now),
        ).fetchone()
    if not row:
        return jsonify({"error": "invalid or expired token"}), 400
    return jsonify({"ok": True, "email": row["email"]})


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=os.environ.get("FLASK_DEBUG") == "1")