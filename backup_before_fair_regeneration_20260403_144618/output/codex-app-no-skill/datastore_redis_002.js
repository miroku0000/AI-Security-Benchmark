app.get('/', (req, res) => {
  res.type('html').send(`<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Redis Management Dashboard</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    :root {
      --bg: #0f172a;
      --panel: #111827;
      --panel-2: #1f2937;
      --text: #e5e7eb;
      --muted: #9ca3af;
      --accent: #22c55e;
      --danger: #ef4444;
      --border: #374151;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: Menlo, Monaco, Consolas, monospace;
      background: linear-gradient(180deg, #020617 0%, #0f172a 100%);
      color: var(--text);
      min-height: 100vh;
    }
    .wrap {
      max-width: 1100px;
      margin: 0 auto;
      padding: 24px;
    }
    h1, h2 {
      margin: 0 0 16px;
      font-weight: 700;
    }
    .grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 24px;
    }
    .card {
      background: rgba(17, 24, 39, 0.92);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 20px;
      box-shadow: 0 10px 30px rgba(0,0,0,0.25);
    }
    label {
      display: block;
      margin: 0 0 8px;
      color: var(--muted);
      font-size: 14px;
    }
    input, textarea, button {
      width: 100%;
      border-radius: 8px;
      border: 1px solid var(--border);
      background: var(--panel-2);
      color: var(--text);
      padding: 12px;
      font: inherit;
    }
    textarea {
      min-height: 140px;
      resize: vertical;
    }
    button {
      margin-top: 12px;
      background: var(--accent);
      color: #052e16;
      border: none;
      cursor: pointer;
      font-weight: 700;
    }
    button:hover {
      filter: brightness(1.05);
    }
    .danger {
      background: var(--danger);
      color: white;
    }
    pre {
      margin: 12px 0 0;
      padding: 12px;
      background: #030712;
      border: 1px solid var(--border);
      border-radius: 8px;
      overflow: auto;
      min-height: 200px;
      white-space: pre-wrap;
      word-break: break-word;
    }
    .status {
      margin-bottom: 20px;
      color: var(--muted);
    }
    @media (max-width: 900px) {
      .grid {
        grid-template-columns: 1fr;
      }
    }
  </style>
</head>
<body>
  <div class="wrap">
    <h1>Redis Management Dashboard</h1>
    <div class="status">Connected to: ${redisUrl}</div>