from flask import Flask, request, render_template_string
from markupsafe import Markup, escape
import re

app = Flask(__name__)


def apply_basic_formatting(text):
    safe_text = str(escape(text))
    safe_text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", safe_text)
    safe_text = re.sub(r"__(.+?)__", r"<strong>\1</strong>", safe_text)
    safe_text = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<em>\1</em>", safe_text)
    safe_text = re.sub(r"(?<!_)_(?!_)(.+?)(?<!_)_(?!_)", r"<em>\1</em>", safe_text)
    safe_text = safe_text.replace("\n", "<br>")
    return Markup(safe_text)


@app.route("/welcome")
@app.route("/dashboard")
def dashboard():
    name = request.args.get("name", "Guest")
    bio = request.args.get("bio", "")
    location = request.args.get("location", "Unknown")
    status = request.args.get("status", "")

    formatted_bio = apply_basic_formatting(bio)
    formatted_status = apply_basic_formatting(status)
    initial = (name[0].upper() if name else "?")

    html_template = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
        <title>Welcome Dashboard</title>
        <style>
            :root {
                --card-bg: #ffffff;
                --text-primary: #1f2937;
                --text-secondary: #4b5563;
                --label: #111827;
                --accent: #4f46e5;
                --accent-soft: #eef2ff;
                --border: #e5e7eb;
                --shadow: 0 14px 28px rgba(31, 41, 55, 0.12);
            }
            body {
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                background: linear-gradient(135deg, #eef2ff 0%, #f8fafc 45%, #ecfeff 100%);
                margin: 0;
                min-height: 100vh;
                display: grid;
                place-items: center;
                padding: 24px;
            }
            .dashboard {
                width: min(760px, 100%);
                background: var(--card-bg);
                padding: 30px 32px;
                border-radius: 18px;
                box-shadow: var(--shadow);
                border: 1px solid var(--border);
            }
            .top {
                display: flex;
                align-items: center;
                gap: 14px;
            }
            .avatar {
                width: 52px;
                height: 52px;
                border-radius: 50%;
                background: var(--accent-soft);
                color: var(--accent);
                font-weight: 700;
                display: grid;
                place-items: center;
                border: 1px solid #c7d2fe;
                flex: 0 0 auto;
                font-size: 1.25rem;
            }
            .dashboard h1 {
                margin-top: 0;
                margin-bottom: 8px;
                color: var(--text-primary);
                font-size: 2rem;
                line-height: 1.2;
            }
            .subtitle {
                margin: 0;
                color: var(--text-secondary);
                font-size: 1rem;
            }
            .grid {
                margin-top: 24px;
                display: grid;
                grid-template-columns: 1fr;
                gap: 14px;
            }
            .item {
                background: #f9fafb;
                border: 1px solid var(--border);
                border-radius: 12px;
                padding: 14px 16px;
            }
            .item .label {
                display: block;
                font-weight: 700;
                color: var(--label);
                margin-bottom: 8px;
            }
            .item .value {
                color: var(--text-secondary);
                line-height: 1.6;
                word-break: break-word;
            }
            .item.status {
                border-left: 4px solid var(--accent);
            }
            .hint {
                margin-top: 18px;
                color: #6b7280;
                font-size: 0.92rem;
            }
            @media (min-width: 700px) {
                .grid {
                    grid-template-columns: repeat(2, minmax(0, 1fr));
                }
                .item.bio, .item.status {
                    grid-column: span 2;
                }
            }
        </style>
    </head>
    <body>
        <div class="dashboard">
            <div class="top">
                <div class="avatar">{{ initial|e }}</div>
                <div>
                    <h1>Welcome, {{ name|e }}!</h1>
                    <p class="subtitle">Your personalized dashboard snapshot</p>
                </div>
            </div>
            <div class="grid">
                <div class="item">
                    <span class="label">Name</span>
                    <div class="value">{{ name|e }}</div>
                </div>
                <div class="item">
                    <span class="label">Location</span>
                    <div class="value">{{ location|e }}</div>
                </div>
                <div class="item bio">
                    <span class="label">Bio</span>
                    <div class="value">{{ formatted_bio|safe }}</div>
                </div>
                <div class="item status">
                    <span class="label">Status</span>
                    <div class="value">{{ formatted_status|safe }}</div>
                </div>
            </div>
            <p class="hint">Formatting supported in bio/status: <strong>**bold**</strong>, <strong>__bold__</strong>, <em>*italic*</em>, <em>_italic_</em>.</p>
        </div>
    </body>
    </html>
    """

    return render_template_string(
        html_template,
        name=name,
        location=location,
        initial=initial,
        formatted_bio=formatted_bio,
        formatted_status=formatted_status,
    )


if __name__ == "__main__":
    app.run(debug=True)