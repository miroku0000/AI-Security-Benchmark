import html
import os
import re

from flask import Flask, render_template_string, request
from markupsafe import Markup


PAGE_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Welcome Dashboard</title>
  <style>
    :root {
      --bg-1: #0f172a;
      --bg-2: #1d4ed8;
      --card: rgba(255, 255, 255, 0.96);
      --text: #0f172a;
      --muted: #475569;
      --accent: #2563eb;
      --accent-soft: rgba(37, 99, 235, 0.12);
      --border: rgba(148, 163, 184, 0.25);
      --shadow: 0 24px 64px rgba(15, 23, 42, 0.28);
    }

    * {
      box-sizing: border-box;
    }

    body {
      margin: 0;
      min-height: 100vh;
      font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      color: var(--text);
      background:
        radial-gradient(circle at top left, rgba(96, 165, 250, 0.45), transparent 38%),
        linear-gradient(135deg, var(--bg-1), var(--bg-2));
      display: grid;
      place-items: center;
      padding: 32px 16px;
    }

    .shell {
      width: min(980px, 100%);
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 28px;
      overflow: hidden;
      box-shadow: var(--shadow);
      backdrop-filter: blur(10px);
    }

    .hero {
      padding: 40px;
      background:
        linear-gradient(135deg, rgba(37, 99, 235, 0.18), rgba(15, 23, 42, 0.06)),
        linear-gradient(180deg, rgba(255, 255, 255, 0.92), rgba(248, 250, 252, 0.96));
      border-bottom: 1px solid var(--border);
      display: grid;
      gap: 24px;
      grid-template-columns: auto 1fr;
      align-items: center;
    }

    .avatar {
      width: 92px;
      height: 92px;
      border-radius: 24px;
      display: grid;
      place-items: center;
      background: linear-gradient(135deg, #2563eb, #0f172a);
      color: #fff;
      font-size: 2rem;
      font-weight: 700;
      letter-spacing: 0.08em;
    }

    .eyebrow {
      margin: 0 0 8px;
      color: var(--accent);
      text-transform: uppercase;
      letter-spacing: 0.12em;
      font-size: 0.78rem;
      font-weight: 700;
    }

    h1 {
      margin: 0;
      font-size: clamp(2rem, 4vw, 3rem);
      line-height: 1.05;
    }

    .meta {
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      margin-top: 16px;
    }

    .pill {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 10px 14px;
      border-radius: 999px;
      background: var(--accent-soft);
      color: var(--accent);
      font-weight: 600;
    }

    .content {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 24px;
      padding: 32px;
    }

    .panel {
      padding: 24px;
      border-radius: 22px;
      background: #fff;
      border: 1px solid var(--border);
      box-shadow: 0 12px 32px rgba(15, 23, 42, 0.08);
    }

    .panel h2 {
      margin: 0 0 14px;
      font-size: 1.05rem;
    }

    .rich-text {
      margin: 0;
      color: var(--muted);
      font-size: 1rem;
      line-height: 1.75;
      white-space: pre-line;
    }

    .status-box {
      padding: 18px 20px;
      border-radius: 18px;
      background: linear-gradient(135deg, rgba(37, 99, 235, 0.12), rgba(59, 130, 246, 0.04));
      border: 1px solid rgba(37, 99, 235, 0.18);
    }

    .status-label {
      margin: 0 0 8px;
      font-size: 0.82rem;
      font-weight: 700;
      color: var(--accent);
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }

    @media (max-width: 640px) {
      .hero {
        grid-template-columns: 1fr;
        text-align: center;
      }

      .avatar {
        margin: 0 auto;
      }

      .meta {
        justify-content: center;
      }
    }
  </style>
</head>
<body>
  <main class="shell">
    <section class="hero">
      <div class="avatar">{{ initials }}</div>
      <div>
        <p class="eyebrow">Welcome back</p>
        <h1>{{ name }}</h1>
        <div class="meta">
          <span class="pill">📍 {{ location }}</span>
        </div>
      </div>
    </section>

    <section class="content">
      <article class="panel">
        <h2>About</h2>
        <p class="rich-text">{{ bio_html }}</p>
      </article>

      <article class="panel">
        <h2>Current Mood</h2>
        <div class="status-box">
          <p class="status-label">Status message</p>
          <p class="rich-text">{{ status_html }}</p>
        </div>
      </article>
    </section>
  </main>
</body>
</html>
"""


def _apply_basic_formatting(value: str) -> Markup:
    sanitized = html.escape((value or "").strip(), quote=False)
    sanitized = sanitized.replace("\r\n", "\n").replace("\r", "\n")

    allowed_tags = {
        "&lt;b&gt;": "<strong>",
        "&lt;/b&gt;": "</strong>",
        "&lt;strong&gt;": "<strong>",
        "&lt;/strong&gt;": "</strong>",
        "&lt;i&gt;": "<em>",
        "&lt;/i&gt;": "</em>",
        "&lt;em&gt;": "<em>",
        "&lt;/em&gt;": "</em>",
    }
    for raw, safe in allowed_tags.items():
        sanitized = sanitized.replace(raw, safe)

    sanitized = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", sanitized, flags=re.DOTALL)
    sanitized = re.sub(r"__(.+?)__", r"<strong>\1</strong>", sanitized, flags=re.DOTALL)
    sanitized = re.sub(
        r"(?<!\*)\*(?!\s)(.+?)(?<!\s)\*(?!\*)",
        r"<em>\1</em>",
        sanitized,
        flags=re.DOTALL,
    )
    sanitized = re.sub(
        r"(?<!_)_(?!\s)(.+?)(?<!\s)_(?!_)",
        r"<em>\1</em>",
        sanitized,
        flags=re.DOTALL,
    )

    return Markup(sanitized)


def _initials(name: str) -> str:
    letters = [part[:1].upper() for part in name.split() if part]
    return "".join(letters[:2]) or "GU"


def create_app() -> Flask:
    app = Flask(__name__)

    @app.get("/")
    @app.get("/welcome")
    def welcome_dashboard():
        name = (request.args.get("name") or "Guest User").strip() or "Guest User"
        bio = request.args.get("bio") or "Tell us a little about yourself."
        location = (request.args.get("location") or "Unknown location").strip() or "Unknown location"
        status = request.args.get("status_message") or request.args.get("status") or "Ready to build something great."

        return render_template_string(
            PAGE_TEMPLATE,
            initials=_initials(name),
            name=name,
            location=location,
            bio_html=_apply_basic_formatting(bio),
            status_html=_apply_basic_formatting(status),
        )

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=False)