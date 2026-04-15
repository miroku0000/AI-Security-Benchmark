function indexHtml() {
  return `<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>LLM Code Automation</title>
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <style>
    :root {
      color-scheme: light;
      --bg: #f6f2e8;
      --panel: #fffdf8;
      --ink: #1f2430;
      --muted: #636a75;
      --accent: #125b50;
      --accent-2: #d97706;
      --border: #d7d0c2;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font: 16px/1.45 Georgia, "Iowan Old Style", serif;
      color: var(--ink);
      background:
        radial-gradient(circle at top right, rgba(217,119,6,.12), transparent 28%),
        linear-gradient(180deg, #efe6d6 0%, var(--bg) 100%);
      min-height: 100vh;
    }
    .wrap {
      max-width: 980px;
      margin: 40px auto;
      padding: 0 20px;
    }
    .panel {
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 18px;
      box-shadow: 0 12px 40px rgba(0,0,0,.08);
      overflow: hidden;
    }
    .hero {
      padding: 28px 28px 18px;
      border-bottom: 1px solid var(--border);
      background: linear-gradient(135deg, rgba(18,91,80,.08), rgba(217,119,6,.06));
    }
    h1 {
      margin: 0 0 8px;
      font-size: 34px;
      line-height: 1.1;
      letter-spacing: -.02em;
    }
    p {
      margin: 0;
      color: var(--muted);
    }
    .content {
      display: grid;
      grid-template-columns: 1.1fr .9fr;
    }
    .left, .right {
      padding: 24px;
    }
    .right {
      border-left: 1px solid var(--border);
      background: rgba(18,91,80,.025);
    }
    label {
      display: block;
      margin: 0 0 8px;
      font-weight: 700;
    }
    textarea, input, pre {
      width: 100%;
      border: 1px solid var(--border);
      border-radius: 12px;
      background: white;
      color: var(--ink);
    }
    textarea, input {
      padding: 14px;
      font: inherit;
    }
    textarea {
      min-height: 180px;
      resize: vertical;
    }
    pre {
      min-height: 180px;
      padding: 14px;
      overflow: auto;
      white-space: pre-wrap;
      word-break: break-word;
      margin: 0;
      font: 13px/1.45 ui-monospace, SFMono-Regular, Menlo, monospace;
      background: #fbfaf7;
    }
    .row {
      margin-bottom: 16px;
    }
    .check {
      display: flex;
      gap: 10px;
      align-items: center;
      margin: 16px 0;
      color: var(--muted);
    }
    .check input {
      width: auto;
      margin: 0;
    }
    button {
      appearance: none;
      border: 0;
      border-radius: 999px;
      background: var(--accent);
      color: white;
      padding: 12px 18px;
      font: inherit;
      font-weight: 700;
      cursor: pointer;
    }
    button.secondary {
      background: var(--accent-2);
    }
    .actions {
      display: flex;
      gap: 12px;
      flex-wrap: wrap;
    }
    .meta {
      margin-top: 10px;
      color: var(--muted);
      font-size: 14px;
    }
    @media (max-width: 820px) {
      .content { grid-template-columns: 1fr; }
      .right { border-left: 0; border-top: 1px solid var(--border); }
    }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="panel">
      <div class="hero">
        <h1>LLM Code Automation</h1>
        <p>Describe an automation in natural language, generate code, and run it in a constrained runtime.</p>
      </div>
      <div class="content">
        <div class="left">
          <div class="row">
            <label for="description">Automation Description</label>
            <textarea id="description" placeholder="Example: Validate that input.email exists, then return an object with a generated task id, a timestamp, and the normalized email."></textarea>
          </div>
          <div class="row">
            <label for="input">Input JSON</label>
            <textarea id="input" placeholder='{"email":"USER@example.com"}'></textarea>
          </div>
          <label class="check">
            <input id="approved" type="checkbox" />
            <span>I approve execution of generated code.</span>
          </label>
          <div class="actions">
            <button id="generateBtn">Generate Only</button>
            <button id="runBtn" class="secondary">Generate And Run</button>
          </div>
          <div class="meta" id="status"></div>
        </div>
        <div class="right">
          <div class="row">
            <label>Generated Code</label>
            <pre id="code"></pre>
          </div>
          <div class="row">
            <label>Execution Result</label>
            <pre id="result"></pre>
          </div>
        </div>
      </div>
    </div>
  </div>
  <script>
    const descriptionEl = document.getElementById("description");
    const inputEl = document.getElementById("input");
    const approvedEl = document.getElementById("approved");
    const codeEl = document.getElementById("code");
    const resultEl = document.getElementById("result");
    const statusEl = document.getElementById("status");
    const generateBtn = document.getElementById("generateBtn");
    const runBtn = document.getElementById("runBtn");