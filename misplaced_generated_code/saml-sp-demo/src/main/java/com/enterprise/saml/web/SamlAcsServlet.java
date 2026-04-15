package com.enterprise.saml.web;

import com.enterprise.saml.SamlProcessingException;
import com.enterprise.saml.SamlResponseProcessor;
import com.enterprise.saml.model.AuthenticatedSession;
import com.enterprise.saml.session.InMemorySessionRegistry;
import jakarta.servlet.http.Cookie;
import jakarta.servlet.http.HttpServlet;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;

import java.io.IOException;
import java.nio.charset.StandardCharsets;

public final class SamlAcsServlet extends HttpServlet {
    public static final String SESSION_COOKIE = "ENTERPRISE_SESSION_ID";

    private final transient SamlResponseProcessor processor;
    private final transient InMemorySessionRegistry sessionRegistry;

    public SamlAcsServlet(SamlResponseProcessor processor, InMemorySessionRegistry sessionRegistry) {
        this.processor = processor;
        this.sessionRegistry = sessionRegistry;
    }

    @Override
    protected void doPost(HttpServletRequest req, HttpServletResponse resp) throws IOException {
        String samlResponse = req.getParameter("SAMLResponse");
        String relayState = req.getParameter("RelayState");
        try {
            AuthenticatedSession session = processor.processInboundSamlResponse(samlResponse);
            sessionRegistry.register(session);
            Cookie cookie = new Cookie(SESSION_COOKIE, session.getSessionId());
            cookie.setPath("/");
            cookie.setHttpOnly(true);
            cookie.setMaxAge(8 * 60 * 60);
            resp.addCookie(cookie);
            String redirect = (relayState != null && !relayState.isBlank()) ? relayState : "/app/me";
            resp.sendRedirect(redirect);
        } catch (SamlProcessingException e) {
            resp.setStatus(HttpServletResponse.SC_BAD_REQUEST);
            resp.setContentType("text/plain;charset=UTF-8");
            resp.getOutputStream().write(("SAML processing failed: " + e.getMessage()).getBytes(StandardCharsets.UTF_8));
        }
    }
}
