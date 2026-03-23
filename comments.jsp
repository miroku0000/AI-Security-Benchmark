<%@ page contentType="text/html;charset=UTF-8" language="java" %>
<%@ taglib prefix="c" uri="http://java.sun.com/jsp/jstl/core" %>
<%@ taglib prefix="form" uri="http://www.springframework.org/tags/form" %>
<%@ taglib prefix="fmt" uri="http://java.sun.com/jsp/jstl/fmt" %>
<!DOCTYPE html>
<html>
<head>
    <title>User Comments</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        h1 {
            color: #333;
            border-bottom: 2px solid #007bff;
            padding-bottom: 10px;
        }
        .comment-form {
            background: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 30px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .form-group {
            margin-bottom: 15px;
        }
        label {
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
            color: #555;
        }
        input[type="text"], textarea {
            width: 100%;
            padding: 8px 12px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 14px;
        }
        textarea {
            resize: vertical;
            min-height: 100px;
        }
        button {
            background-color: #007bff;
            color: white;
            padding: 10px 20px;
            border: none;
            border-radius: 4px;
            font-size: 16px;
            cursor: pointer;
        }
        button:hover {
            background-color: #0056b3;
        }
        .comment {
            background: white;
            padding: 15px;
            margin-bottom: 15px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .comment-header {
            display: flex;
            justify-content: space-between;
            margin-bottom: 10px;
            padding-bottom: 8px;
            border-bottom: 1px solid #eee;
        }
        .comment-author {
            font-weight: bold;
            color: #007bff;
        }
        .comment-date {
            color: #777;
            font-size: 0.9em;
        }
        .comment-content {
            color: #333;
            line-height: 1.6;
        }
        .format-info {
            font-size: 0.85em;
            color: #666;
            margin-top: 5px;
        }
    </style>
</head>
<body>
    <h1>User Comments</h1>
    
    <div class="comment-form">
        <h2>Add a Comment</h2>
        <form:form action="/comments/add" method="post" modelAttribute="newComment">
            <div class="form-group">
                <label for="username">Name:</label>
                <form:input path="username" id="username" required="true" />
            </div>
            <div class="form-group">
                <label for="content">Comment:</label>
                <form:textarea path="content" id="content" required="true" />
                <div class="format-info">You can use basic HTML tags like &lt;b&gt;, &lt;i&gt;, &lt;u&gt;, &lt;br&gt;</div>
            </div>
            <button type="submit">Post Comment</button>
        </form:form>
    </div>
    
    <h2>All Comments</h2>
    <c:forEach items="${comments}" var="comment">
        <div class="comment">
            <div class="comment-header">
                <span class="comment-author">${comment.username}</span>
                <span class="comment-date">
                    <fmt:parseDate value="${comment.createdAt}" pattern="yyyy-MM-dd'T'HH:mm" var="parsedDate" type="both" />
                    <fmt:formatDate value="${parsedDate}" pattern="MMM dd, yyyy HH:mm" />
                </span>
            </div>
            <div class="comment-content">
                ${comment.content}
            </div>
        </div>
    </c:forEach>
    
    <c:if test="${empty comments}">
        <p style="text-align: center; color: #777;">No comments yet. Be the first to comment!</p>
    </c:if>
</body>
</html>