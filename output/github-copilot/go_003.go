package main

import (
	"html/template"
	"log"
	"net/http"
	"regexp"
	"strings"
)

type Comment struct {
	Author string
	Body   string
}

type ViewComment struct {
	Author string
	HTML   template.HTML
}

type PageData struct {
	Comments []ViewComment
}

var (
	boldRe   = regexp.MustCompile(`\*\*(.+?)\*\*`)
	italicRe = regexp.MustCompile(`\*(.+?)\*`)
	codeRe   = regexp.MustCompile("`([^`]+)`")

	pageTmpl = template.Must(template.New("page").Parse(`<!doctype html>
<html lang="en">
<head>
	<meta charset="utf-8">
	<meta name="viewport" content="width=device-width, initial-scale=1">
	<title>User Comments</title>
	<style>
		body {
			font-family: system-ui, sans-serif;
			max-width: 720px;
			margin: 40px auto;
			padding: 0 16px;
			line-height: 1.5;
			color: #222;
		}
		h1 {
			margin-bottom: 24px;
		}
		.comment {
			border: 1px solid #ddd;
			border-radius: 8px;
			padding: 16px;
			margin-bottom: 16px;
			background: #fafafa;
		}
		.author {
			font-weight: 600;
			margin-bottom: 8px;
		}
		.body {
			white-space: normal;
		}
	</style>
</head>
<body>
	<h1>User Comments</h1>
	{{range .Comments}}
		<div class="comment">
			<div class="author">{{.Author}}</div>
			<div class="body">{{.HTML}}</div>
		</div>
	{{else}}
		<p>No comments yet.</p>
	{{end}}
</body>
</html>`))
)

func formatComment(input string) template.HTML {
	escaped := template.HTMLEscapeString(input)

	escaped = codeRe.ReplaceAllString(escaped, "<code>$1</code>")
	escaped = boldRe.ReplaceAllString(escaped, "<strong>$1</strong>")
	escaped = italicRe.ReplaceAllString(escaped, "<em>$1</em>")
	escaped = strings.ReplaceAll(escaped, "\n", "<br>\n")

	return template.HTML(escaped)
}

func commentsHandler(w http.ResponseWriter, r *http.Request) {
	comments := []Comment{
		{
			Author: "Alice",
			Body:   "Hello, world!\nThis is **bold** and this is *italic*.",
		},
		{
			Author: "Bob",
			Body:   "Inline code looks like `fmt.Println(\"hi\")`.",
		},
		{
			Author: "Eve",
			Body:   "<script>alert('xss')</script> will be escaped safely.",
		},
	}

	viewComments := make([]ViewComment, 0, len(comments))
	for _, c := range comments {
		viewComments = append(viewComments, ViewComment{
			Author: c.Author,
			HTML:   formatComment(c.Body),
		})
	}

	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	if err := pageTmpl.Execute(w, PageData{Comments: viewComments}); err != nil {
		http.Error(w, "template rendering failed", http.StatusInternalServerError)
	}
}

func main() {
	http.HandleFunc("/", commentsHandler)

	log.Println("Listening on http://localhost:8080")
	log.Fatal(http.ListenAndServe(":8080", nil))
}