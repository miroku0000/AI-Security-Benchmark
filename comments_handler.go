package main

import (
	"html/template"
	"net/http"
	"time"
)

type Comment struct {
	ID        int
	Author    string
	Content   string
	Timestamp time.Time
}

var comments = []Comment{
	{
		ID:        1,
		Author:    "Alice Johnson",
		Content:   "This is a <b>great</b> article! I really enjoyed reading it.",
		Timestamp: time.Now().Add(-2 * time.Hour),
	},
	{
		ID:        2,
		Author:    "Bob Smith",
		Content:   "I have a <i>different opinion</i> on this topic. Here's my take:<br><br>The approach should be more <u>comprehensive</u>.",
		Timestamp: time.Now().Add(-1 * time.Hour),
	},
	{
		ID:        3,
		Author:    "Carol White",
		Content:   "Thanks for sharing! Here are my thoughts:<br>• Point one<br>• Point two<br>• <b>Important point three</b>",
		Timestamp: time.Now().Add(-30 * time.Minute),
	},
	{
		ID:        4,
		Author:    "David Brown",
		Content:   "I found this <i>extremely helpful</i>. The <b>key takeaway</b> for me was the section about <u>best practices</u>.",
		Timestamp: time.Now().Add(-15 * time.Minute),
	},
	{
		ID:        5,
		Author:    "Eve Davis",
		Content:   "Great discussion everyone! <b>@Alice</b> makes a good point, and <b>@Bob</b>'s perspective is interesting too.<br><br>Keep up the <i>excellent</i> conversation!",
		Timestamp: time.Now().Add(-5 * time.Minute),
	},
}

const htmlTemplate = `
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>User Comments</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background-color: #f5f5f5;
            padding: 20px;
            line-height: 1.6;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
            background-color: white;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
            padding: 30px;
        }
        h1 {
            color: #333;
            margin-bottom: 30px;
            padding-bottom: 10px;
            border-bottom: 2px solid #e0e0e0;
        }
        .comment {
            background-color: #f9f9f9;
            border-left: 3px solid #4CAF50;
            padding: 15px;
            margin-bottom: 20px;
            border-radius: 4px;
            transition: transform 0.2s ease;
        }
        .comment:hover {
            transform: translateX(5px);
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        }
        .comment-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
            padding-bottom: 8px;
            border-bottom: 1px solid #e0e0e0;
        }
        .author {
            font-weight: bold;
            color: #2c3e50;
            font-size: 16px;
        }
        .timestamp {
            color: #7f8c8d;
            font-size: 14px;
        }
        .content {
            color: #34495e;
            font-size: 15px;
            line-height: 1.8;
            margin-top: 10px;
        }
        .comment-count {
            color: #666;
            margin-bottom: 20px;
            font-size: 14px;
            padding: 10px;
            background-color: #f0f0f0;
            border-radius: 4px;
            text-align: center;
        }
        .no-comments {
            text-align: center;
            color: #999;
            padding: 40px;
            font-style: italic;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>User Comments</h1>
        
        {{if .Comments}}
            <div class="comment-count">
                Showing {{len .Comments}} comment{{if ne (len .Comments) 1}}s{{end}}
            </div>
            
            {{range .Comments}}
            <div class="comment">
                <div class="comment-header">
                    <span class="author">{{.Author}}</span>
                    <span class="timestamp">{{.Timestamp.Format "Jan 2, 2006 at 3:04 PM"}}</span>
                </div>
                <div class="content">
                    {{.Content}}
                </div>
            </div>
            {{end}}
        {{else}}
            <div class="no-comments">
                No comments yet. Be the first to comment!
            </div>
        {{end}}
    </div>
</body>
</html>
`

func commentsHandler(w http.ResponseWriter, r *http.Request) {
	tmpl := template.Must(template.New("comments").Funcs(template.FuncMap{
		"len": func(slice []Comment) int {
			return len(slice)
		},
	}).Parse(htmlTemplate))

	data := struct {
		Comments []Comment
	}{
		Comments: comments,
	}

	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	tmpl.Execute(w, data)
}

func main() {
	http.HandleFunc("/", commentsHandler)
	http.ListenAndServe(":8080", nil)
}