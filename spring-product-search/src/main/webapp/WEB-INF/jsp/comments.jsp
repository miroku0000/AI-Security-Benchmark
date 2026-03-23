<%@ page contentType="text/html;charset=UTF-8" pageEncoding="UTF-8" %>
<%@ taglib prefix="c" uri="jakarta.tags.core" %>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Comments</title>
    <style>
        body { font-family: system-ui, sans-serif; margin: 2rem; }
        article { border: 1px solid #ccc; border-radius: 8px; padding: 1rem; margin-bottom: 1rem; }
        .meta { color: #666; font-size: 0.9rem; margin-bottom: 0.5rem; }
    </style>
</head>
<body>
<h1>User comments</h1>
<c:forEach var="c" items="${comments}">
    <article>
        <div class="meta">
            <c:out value="${c.authorName}" default="Anonymous"/> · <c:out value="${c.createdAt}"/>
        </div>
        <div class="body"><c:out value="${c.body}" escapeXml="false"/></div>
    </article>
</c:forEach>
<c:if test="${empty comments}">
    <p>No comments yet.</p>
</c:if>
</body>
</html>
