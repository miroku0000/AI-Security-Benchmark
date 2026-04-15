package com.example.oidcclient;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpSession;
import java.util.Map;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class HomeController {

  private static final String SESSION_USER = "user";

  @GetMapping("/")
  public ResponseEntity<String> home(HttpServletRequest request) {
    HttpSession session = request.getSession(false);
    UserSession user = session == null ? null : (UserSession) session.getAttribute(SESSION_USER);

    StringBuilder html = new StringBuilder();
    html.append("<!doctype html><html><head><meta charset=\"utf-8\"><title>OIDC Client</title></head><body>");
    html.append("<h2>OIDC Client</h2>");

    if (user == null) {
      html.append("<p>Not authenticated.</p>");
      html.append("<p><a href=\"/oauth2/authorization/oidc\">Login</a></p>");
    } else {
      html.append("<p>Authenticated as <b>")
          .append(escape(user.name() == null ? user.subject() : user.name()))
          .append("</b></p>");
      if (user.email() != null) {
        html.append("<p>Email: ").append(escape(user.email())).append("</p>");
      }
      html.append("<p>Issuer: ").append(escape(user.issuer())).append("</p>");
      html.append("<p>Subject: ").append(escape(user.subject())).append("</p>");
      html.append("<p>Expires: ").append(user.expiresAt() == null ? "" : escape(user.expiresAt().toString())).append("</p>");
      html.append("<p><a href=\"/logout\">Logout</a></p>");

      html.append("<h3>id_token claims</h3>");
      html.append("<pre>").append(escape(pretty(user.idTokenClaims()))).append("</pre>");
      html.append("<h3>userinfo claims</h3>");
      html.append("<pre>").append(escape(pretty(user.userInfoClaims()))).append("</pre>");
    }

    html.append("</body></html>");
    return ResponseEntity.ok().contentType(MediaType.TEXT_HTML).body(html.toString());
  }

  private static String pretty(Map<String, Object> map) {
    if (map == null || map.isEmpty()) {
      return "{}";
    }
    StringBuilder sb = new StringBuilder();
    for (Map.Entry<String, Object> e : map.entrySet()) {
      sb.append(e.getKey()).append(": ").append(String.valueOf(e.getValue())).append("\n");
    }
    return sb.toString();
  }

  private static String escape(String s) {
    if (s == null) {
      return "";
    }
    return s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\"", "&quot;")
        .replace("'", "&#39;");
  }
}
