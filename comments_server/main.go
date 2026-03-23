package main

import (
	"html/template"
	"log"
	"net/http"
)

type Comment struct {
	Author string
	Body   template.HTML
}

var comments = []Comment{
	{Author: "Alice", Body: "Thanks for the post! <b>Great work</b>."},
	{Author: "Bob", Body: "Could you add more detail on <i>step two</i>?"},
	{Author: "Carol", Body: "Here is a <a href=\"https://example.com\">link</a> for reference."},
}

var pageTmpl = template.Must(template.New("comments").Parse(`<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Comments</title>
<style>
body { font-family: system-ui, sans-serif; max-width: 40rem; margin: 2rem auto; padding: 0 1rem; }
article { border: 1px solid #ccc; border-radius: 8px; padding: 1rem; margin-bottom: 1rem; }
cite { color: #555; font-style: normal; font-weight: 600; }
</style>
</head>
<body>
<h1>Comments</h1>
{{range .}}
<article>
<p><cite>{{.Author}}</cite></p>
<div class="body">{{.Body}}</div>
</article>
{{end}}
</body>
</html>
`))

func commentsHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}
	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	if err := pageTmpl.Execute(w, comments); err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
	}
}

func main() {
	http.HandleFunc("/", commentsHandler)
	log.Fatal(http.ListenAndServe(":8080", nil))
}
