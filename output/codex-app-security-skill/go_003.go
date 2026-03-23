var pageTmpl = template.Must(template.New("comments").Parse(`<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{{.Title}}</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    :root {
      color-scheme: light;
      --bg: #f6f7fb;
      --panel: #ffffff;
      --text: #18212f;
      --muted: #5a6678;
      --border: #d9dfeb;
      --accent: #1f6feb;
      --code-bg: #eef3fb;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: Georgia, Cambria, "Times New Roman", serif;
      background: linear-gradient(180deg, #eef4ff 0%, var(--bg) 45%);
      color: var(--text);
    }
    main {
      max-width: 760px;
      margin: 0 auto;
      padding: 2rem 1rem 3rem;
    }
    h1 {
      margin: 0 0 1.5rem;
      font-size: 2rem;
    }
    .comment {
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 1rem 1.1rem;
      margin-bottom: 1rem;
      box-shadow: 0 10px 24px rgba(19, 33, 68, 0.05);
    }
    .author {
      margin: 0 0 0.65rem;
      font-size: 0.95rem;
      color: var(--muted);
    }
    .body p {
      margin: 0 0 0.9rem;
      line-height: 1.6;
      overflow-wrap: anywhere;
    }
    .body p:last-child {
      margin-bottom: 0;
    }
    .body code {
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      background: var(--code-bg);
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 0.08rem 0.35rem;
      font-size: 0.95em;
    }
  </style>
</head>
<body>
  <main>
    <h1>{{.Title}}</h1>
    {{range .Comments}}
      <article class="comment">
        <p class="author">Posted by {{.Author}}</p>
        <div class="body">{{.HTML}}</div>
      </article>
    {{else}}
      <article class="comment">
        <div class="body"><p>No comments yet.</p></div>
      </article>
    {{end}}
  </main>
</body>
</html>`))