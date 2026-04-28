import os
import secrets
import smtplib
import sqlite3
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage

from flask import Flask, jsonify, request


app = Flask(__name__)

DATABASE_PATH = os.getenv("DATABASE_PATH", "password_reset.db")
RESET_BASE_URL = os.getenv("RESET_BASE_URL", "http://localhost:5000/reset-password")
SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "true").lower() == "true"
EMAIL_FROM = os.getenv("EMAIL_FROM", "no-reply@example.com")


def get_db_connection():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    with get_db_connection() as connection:
        connection.execute(
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
        connection.commit()


def generate_reset_token():
    return secrets.token_urlsafe(32)


def build_reset_link(token):
    separator = "&" if "?" in RESET_BASE_URL else "?"
    return f"{RESET_BASE_URL}{separator}token={token}"


def store_reset_token(email, token):
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(hours=1)

    with get_db_connection() as connection:
        connection.execute(
            """
            INSERT INTO password_reset_tokens (email, token, created_at, expires_at)
            VALUES (?, ?, ?, ?)
            """,
            (email, token, now.isoformat(), expires_at.isoformat()),
        )
        connection.commit()


def send_reset_email(recipient_email, reset_link):
    subject = "Password reset"
    body = f"Use this link to reset your password: {reset_link}"

    if not SMTP_HOST:
        print(f"Password reset link for {recipient_email}: {reset_link}")
        return

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = EMAIL_FROM
    message["To"] = recipient_email
    message.set_content(body)

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as smtp:
        if SMTP_USE_TLS:
            smtp.starttls()
        if SMTP_USERNAME and SMTP_PASSWORD:
            smtp.login(SMTP_USERNAME, SMTP_PASSWORD)
        smtp.send_message(message)


@app.post("/password-reset")
def request_password_reset():
    payload = request.get_json(silent=True) or {}
    email = str(payload.get("email", "")).strip().lower()

    if not email:
        return jsonify({"error": "email is required"}), 400

    token = generate_reset_token()
    store_reset_token(email, token)
    reset_link = build_reset_link(token)
    send_reset_email(email, reset_link)

    return jsonify({"message": "If the email exists, a reset link has been sent."}), 200


init_db()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=False)