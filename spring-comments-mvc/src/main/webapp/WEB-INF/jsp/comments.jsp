<%@ page contentType="text/html;charset=UTF-8" pageEncoding="UTF-8" %>
<%@ taglib uri="jakarta.tags.core" prefix="c" %>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Comments</title>
    <style>
        body { font-family: system-ui, sans-serif; margin: 2rem; }
        article { border: 1px solid #ccc; border-radius: 8px; padding: 1rem; margin-bottom: 1rem; }
        .author { color: #555; font-size: 0.9rem; margin-bottom: 0.5rem; }
    </style>
</head>
<body>
<h1>User comments</h1>
<c:choose>
    <c:when test="${empty comments}">
        <p>No comments yet.</p>
    </c:when>
    <c:otherwise>
        <c:forEach var="comment" items="${comments}">
            <article>
                <div class="author"><c:out value="${comment.author}" escapeXml="true"/></div>
                <div class="body"><c:out value="${comment.body}" escapeXml="false"/></div>
            </article>
        </c:forEach>
    </c:otherwise>
</c:choose>
</body>
</html>
