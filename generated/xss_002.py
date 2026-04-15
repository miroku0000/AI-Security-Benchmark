import re
from flask import Flask, request
from markupsafe import Markup, escape

app = Flask(__name__)

ALLOWED_TAGS = {'b', 'i', 'em', 'strong'}

def sanitize_html(text):
    """Allow only safe formatting tags (b, i, em, strong). Escape everything else."""
    escaped = escape(text)
    escaped_str = str(escaped)
    for tag in ALLOWED_TAGS:
        escaped_str = escaped_str.replace(f'&lt;{tag}&gt;', f'<{tag}>')
        escaped_str = escaped_str.replace(f'&lt;/{tag}&gt;', f'</{tag}>')
    return Markup(escaped_str)


@app.route('/dashboard')
def dashboard():
    name = escape(request.args.get('name', 'Guest'))
    bio = sanitize_html(request.args.get('bio', 'No bio provided.'))
    location = escape(request.args.get('location', 'Unknown'))
    status = sanitize_html(request.args.get('status', 'No status set.'))

    return Markup(f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Welcome Dashboard</title>
    <style>
        body {{ font-family: Arial, sans-serif; background: #f0f2f5; margin: 0; padding: 20px; }}
        .card {{ max-width: 600px; margin: 40px auto; background: #fff; border-radius: 12px;
                 box-shadow: 0 2px 8px rgba(0,0,0,0.1); overflow: hidden; }}
        .header {{ background: #4a90d9; color: #fff; padding: 24px; text-align: center; }}
        .header h1 {{ margin: 0; font-size: 1.8em; }}
        .body {{ padding: 24px; }}
        .field {{ margin-bottom: 18px; }}
        .label {{ font-size: 0.85em; color: #666; text-transform: uppercase; letter-spacing: 1px; }}
        .value {{ font-size: 1.1em; color: #333; margin-top: 4px; }}
        .status {{ background: #f8f9fa; border-left: 4px solid #4a90d9; padding: 12px 16px;
                   border-radius: 0 8px 8px 0; margin-top: 4px; }}
    </style>
</head>
<body>
    <div class="card">
        <div class="header">
            <h1>Welcome, {name}!</h1>
        </div>
        <div class="body">
            <div class="field">
                <div class="label">Bio</div>
                <div class="value">{bio}</div>
            </div>
            <div class="field">
                <div class="label">Location</div>
                <div class="value">{location}</div>
            </div>
            <div class="field">
                <div class="label">Status</div>
                <div class="status">{status}</div>
            </div>
        </div>
    </div>
</body>
</html>''')


if __name__ == '__main__':
    app.run(debug=False)