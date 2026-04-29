<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Blog Comments</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .post {
            background: white;
            padding: 20px;
            margin-bottom: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .post h1 {
            margin-top: 0;
            color: #333;
        }
        .comments-section {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .comments-section h2 {
            margin-top: 0;
            color: #333;
            border-bottom: 2px solid #007bff;
            padding-bottom: 10px;
        }
        .comment {
            padding: 15px;
            margin-bottom: 15px;
            border-left: 3px solid #007bff;
            background-color: #f9f9f9;
        }
        .comment-header {
            display: flex;
            justify-content: space-between;
            margin-bottom: 10px;
            font-size: 0.9em;
            color: #666;
        }
        .comment-author {
            font-weight: bold;
            color: #007bff;
        }
        .comment-date {
            color: #999;
        }
        .comment-content {
            line-height: 1.6;
            color: #333;
        }
        .comment-content a {
            color: #007bff;
            text-decoration: none;
        }
        .comment-content a:hover {
            text-decoration: underline;
        }
    </style>
</head>
<body>
    <div class="post">
        <h1>{{ $post->title }}</h1>
        <div class="post-content">
            {{ $post->body }}
        </div>
    </div>

    <div class="comments-section">
        <h2>Comments ({{ $comments->count() }})</h2>
        
        @forelse($comments as $comment)
            <div class="comment">
                <div class="comment-header">
                    <span class="comment-author">{{ $comment->author_name }}</span>
                    <span class="comment-date">{{ $comment->created_at->format('M d, Y - H:i') }}</span>
                </div>
                <div class="comment-content">
                    {!! $comment->content !!}
                </div>
            </div>
        @empty
            <p>No comments yet. Be the first to comment!</p>
        @endforelse
    </div>
</body>
</html>