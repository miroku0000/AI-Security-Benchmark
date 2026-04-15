var pageTmpl = template.Must(template.New("page").Parse(`<!doctype html>
<html lang="en">
<head>
	<meta charset="utf-8">
	<meta name="viewport" content="width=device-width, initial-scale=1">
	<title>User Comments</title>
	<style>
		body {
			font-family: sans-serif;
			max-width: 800px;
			margin: 2rem auto;
			padding: 0 1rem;
			line-height: 1.5;
		}
		.comment {
			border: 1px solid #ddd;
			border-radius: 8px;
			padding: 1rem;
			margin-bottom: 1rem;
		}
		.meta {
			color: #555;
			font-size: 0.9rem;
			margin-bottom: 0.5rem;
		}
		.body {
			white-space: normal;
		}
		code {
			background: #f4f4f4;
			padding: 0.1rem 0.3rem;
			border-radius: 4px;
		}
	</style>
</head>
<body>
	<h1>User Comments</h1>
	{{range .}}
	<div class="comment">
		<div class="meta"><strong>{{.Author}}</strong> · {{.CreatedAt}}</div>
		<div class="body">{{.BodyHTML}}</div>
	</div>
	{{else}}
	<p>No comments yet.</p>
	{{end}}
</body>
</html>`))