import (
	"html"
	"html/template"
	"net/http"
	"strings"
)

type Comment struct {
	Author string
	Body   string
}

type commentView struct {
	Author    string
	Formatted template.HTML
}

func formatComment(body string) template.HTML {
	escaped := html.EscapeString(body)
	escaped = strings.ReplaceAll(escaped, "\n", "<br>")
	return template.HTML(escaped)
}

func main() {
	comments := []Comment{
		{Author: "Alice", Body: "Hello everyone!\nThis is my first comment."},
		{Author: "Bob", Body: "Thanks for sharing.\nLine two here."},
		{Author: "Carol", Body: "Nice work on the project."},
	}

	tmpl := template.Must(template.New("page").Parse(`<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Comments</title>
<style>
body { font-family: system-ui, sans-serif; max-width: 40rem; margin: 2rem auto; }
article { border: 1px solid #ccc; border-radius: 8px; padding: 1rem; margin-bottom: 1rem; }
.author { font-weight: 600; margin-bottom: 0.5rem; }
</style>
</head>
<body>
<h1>Comments</h1>
{{range .}}
<article>
<div class="author">{{.Author}}</div>
<div class="body">{{.Formatted}}</div>
</article>
{{end}}
</body>
</html>`))

	http.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/" {
			http.NotFound(w, r)
			return
		}
		views := make([]commentView, len(comments))
		for i, c := range comments {
			views[i] = commentView{Author: c.Author, Formatted: formatComment(c.Body)}
		}
		w.Header().Set("Content-Type", "text/html; charset=utf-8")
		if err := tmpl.Execute(w, views); err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
		}
	})

	_ = http.ListenAndServe(":8080", nil)
}