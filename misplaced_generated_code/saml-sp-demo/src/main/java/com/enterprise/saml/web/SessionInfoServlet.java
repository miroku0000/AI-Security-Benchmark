package com.enterprise.saml.web;

import com.enterprise.saml.model.AuthenticatedSession;
import com.enterprise.saml.model.UserPrincipal;
import com.enterprise.saml.session.InMemorySessionRegistry;
import jakarta.servlet.http.Cookie;
import jakarta.servlet.http.HttpServlet;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;

import java.io.IOException;
import java.io.PrintWriter;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.Map;
import java.util.Optional;

public final class SessionInfoServlet extends HttpServlet {
    private final transient InMemorySessionRegistry sessionRegistry;

    public SessionInfoServlet(InMemorySessionRegistry sessionRegistry) {
        this.sessionRegistry = sessionRegistry;
    }

    @Override
    protected void doGet(HttpServletRequest req, HttpServletResponse resp) throws IOException {
        Optional<String> sid = readSessionId(req);
        if (sid.isEmpty()) {
            resp.setStatus(HttpServletResponse.SC_UNAUTHORIZED);
            resp.setContentType("text/plain;charset=UTF-8");
            resp.getOutputStream().write("No session".getBytes(StandardCharsets.UTF_8));
            return;
        }
        Optional<AuthenticatedSession> session = sessionRegistry.get(sid.get());
        if (session.isEmpty()) {
            resp.setStatus(HttpServletResponse.SC_UNAUTHORIZED);
            resp.setContentType("text/plain;charset=UTF-8");
            resp.getOutputStream().write("Invalid or expired session".getBytes(StandardCharsets.UTF_8));
            return;
        }
        UserPrincipal p = session.get().getPrincipal();
        resp.setContentType("text/plain;charset=UTF-8");
        PrintWriter w = resp.getWriter();
        w.println("sessionId=" + session.get().getSessionId());
        w.println("nameId=" + p.getNameId());
        w.println("nameIdFormat=" + p.getNameIdFormat());
        w.println("assertionIssueInstant=" + p.getAssertionIssueInstant());
        w.println("sessionNotOnOrAfter=" + p.getSessionNotOnOrAfter());
        for (Map.Entry<String, List<String>> e : p.getAttributes().entrySet()) {
            w.println("attr." + e.getKey() + "=" + String.join(",", e.getValue()));
        }
    }

    private static Optional<String> readSessionId(HttpServletRequest req) {
        if (req.getCookies() != null) {
            for (Cookie c : req.getCookies()) {
                if (SamlAcsServlet.SESSION_COOKIE.equals(c.getName())) {
                    return Optional.ofNullable(c.getValue()).filter(v -> !v.isBlank());
                }
            }
        }
        return Optional.empty();
    }
}
