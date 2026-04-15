def graphiql_html():
    return """<!doctype html>
<html>
  <head>
    <meta charset="utf-8">
    <title>GraphQL API</title>
    <style>
      body { margin: 0; font-family: sans-serif; }
      #query { width: 100%; height: 260px; }
      #variables { width: 100%; height: 120px; }
      #output { white-space: pre-wrap; background: #111; color: #eee; padding: 16px; min-height: 220px; }
      .wrap { max-width: 900px; margin: 24px auto; padding: 0 16px; }
      button { padding: 10px 16px; }
      input { width: 100%; padding: 8px; }
      label { display: block; margin: 12px 0 6px; }
    </style>
  </head>
  <body>
    <div class="wrap">
      <h1>GraphQL API</h1>
      <p>Use Authorization header like: <code>Bearer user-1</code></p>
      <label>Authorization</label>
      <input id="auth" value="Bearer user-1" />
      <label>Query</label>
      <textarea id="query">query {
  me {
    id
    username
    email
    bio
    role
    isAdmin
    credits
    subscriptionTier
  }
}</textarea>
      <label>Variables (JSON)</label>
      <textarea id="variables">{}</textarea>
      <p><button onclick="runQuery()">Run</button></p>
      <pre id="output"></pre>
    </div>
    <script>
      async function runQuery() {
        const query = document.getElementById("query").value;
        const variablesText = document.getElementById("variables").value || "{}";
        const auth = document.getElementById("auth").value;
        let variables = {};
        try {
          variables = JSON.parse(variablesText);
        } catch (e) {
          document.getElementById("output").textContent = "Invalid variables JSON: " + e.message;
          return;
        }