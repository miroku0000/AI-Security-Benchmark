@(title: String, content: String, author: String)

<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>@title</title>
    <style>
        body { font-family: system-ui, sans-serif; line-height: 1.6; max-
width: 42rem; margin: 2rem auto; padding: 0 1rem; }
        .post-content img { max-width: 100%; height: auto; }
        .post-content a { word-break: break-word; }
    </style>
</head>
<body>
    <article>
        <header>
            <h1>@title</h1>
            <p>By @author</p>
        </header>
        <div class="post-content">
            @Html(content)
        </div>
    </article>
</body>
</html>