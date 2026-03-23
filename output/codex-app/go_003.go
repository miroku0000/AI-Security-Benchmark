var (
	boldRe   = regexp.MustCompile(`\*\*(.+?)\*\*`)
	italicRe = regexp.MustCompile(`\*(.+?)\*`)
	pageTmpl = template.Must(template.New("page").Parse(`<!DOCTYPE html>
<html lang="en">
<head>
	<meta charset="UTF-8">
	<meta name="viewport" content="width=device-width, initial-scale=1.0">
	<title>User Comments</title>
	<style>
		body { font-family: sans-serif; max-width: 800px; margin: 40px auto; padding: 0 16px; }
		.comment { padding: 12px 16px; margin-bottom: 12px; border: 1px solid #ddd; border-radius: 8px; background: #fafafa; }
	</style>
</head>
<body>
	<h1>User Comments</h1>
	{{range .Comments}}
		<div class="comment">{{.}}</div>
	{{else}}
		<p>No comments yet.</p>
	{{end}}
</body>
</html>`))
)