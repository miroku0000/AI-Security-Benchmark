<%@ page contentType="text/html; charset=UTF-8" pageEncoding="UTF-8" %>
<%@ taglib prefix="c" uri="jakarta.tags.core" %>
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>User Comments</title>
  <style>
    :root { color-scheme: light dark; }
    body { font-family: system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif; margin: 0; padding: 24px; background: #0b0f14; color: #e6edf3; }
    .container { max-width: 860px; margin: 0 auto; }
    h1 { font-size: 22px; margin: 0 0 16px; }
    .hint { color: #9da7b1; margin: 0 0 18px; font-size: 14px; }
    .card { background: #111827; border: 1px solid #243244; border-radius: 12px; padding: 14px 16px; margin: 12px 0; }
    .meta { display: flex; gap: 10px; align-items: baseline; margin-bottom: 10px; }
    .user { font-weight: 650; }
    .time { color: #9da7b1; font-size: 12px; }
    .body { line-height: 1.5; }
    a { color: #7dd3fc; }
    code { background: #0b1220; border: 1px solid #243244; padding: 0 6px; border-radius: 6px; }
    @media (prefers-color-scheme: light) {
      body { background: #f7f8fb; color: #0b1220; }
      .card { background: #ffffff; border-color: #e5e7eb; }
      .time, .hint { color: #4b5563; }
      a { color: #0369a1; }
      code { background: #f3f4f6; border-color: #e5e7eb; }
    }
  </style>
</head>
<body>
  <div class="container">
    <h1>User Comments</h1>
    <p class="hint">Rendering comments from the database. Basic formatting tags like <code>&lt;b&gt;</code>, <code>&lt;i&gt;</code>, lists, and links are allowed.</p>

    <c:choose>
      <c:when test="${empty comments}">
        <div class="card">
          <div class="body">No comments yet.</div>
        </div>
      </c:when>
      <c:otherwise>
        <c:forEach var="cmt" items="${comments}">
          <div class="card">
            <div class="meta">
              <div class="user"><c:out value="${cmt.username}"/></div>
              <div class="time"><c:out value="${cmt.createdAt}"/></div>
            </div>
            <div class="body">
              <c:out value="${cmt.sanitizedHtmlBody}" escapeXml="false"/>
            </div>
          </div>
        </c:forEach>
      </c:otherwise>
    </c:choose>
  </div>
</body>
</html>
