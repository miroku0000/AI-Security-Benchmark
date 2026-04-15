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