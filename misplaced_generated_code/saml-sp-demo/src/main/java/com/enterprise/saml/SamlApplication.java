package com.enterprise.saml;

import com.enterprise.saml.model.AuthenticatedSession;
import com.enterprise.saml.model.UserPrincipal;
import com.enterprise.saml.session.InMemorySessionRegistry;
import com.enterprise.saml.web.SamlAcsServlet;
import com.enterprise.saml.web.SessionInfoServlet;
import org.eclipse.jetty.server.Server;
import org.eclipse.jetty.servlet.ServletContextHandler;
import org.eclipse.jetty.servlet.ServletHolder;

import java.io.InputStream;
import java.util.Base64;
import java.util.List;
import java.util.Map;

public final class SamlApplication {
    public static void main(String[] args) throws Exception {
        if (args.length > 0 && "--demo-parse".equals(args[0])) {
            runOfflineDemo();
            return;
        }
        InMemorySessionRegistry registry = new InMemorySessionRegistry();
        SamlResponseProcessor processor = new SamlResponseProcessor();
        Server server = new Server(8080);
        ServletContextHandler context = new ServletContextHandler(ServletContextHandler.SESSIONS);
        context.setContextPath("/");
        context.addServlet(new ServletHolder(new SamlAcsServlet(processor, registry)), "/saml/acs");
        context.addServlet(new ServletHolder(new SessionInfoServlet(registry)), "/app/me");
        server.setHandler(context);
        server.start();
        server.join();
    }

    private static void runOfflineDemo() throws Exception {
        byte[] xml;
        try (InputStream in = SamlApplication.class.getResourceAsStream("/sample-saml-response.xml")) {
            if (in == null) {
                throw new IllegalStateException("Missing /sample-saml-response.xml");
            }
            xml = in.readAllBytes();
        }
        String b64 = Base64.getEncoder().encodeToString(xml);
        SamlResponseProcessor processor = new SamlResponseProcessor();
        AuthenticatedSession session = processor.processInboundSamlResponse(b64);
        UserPrincipal p = session.getPrincipal();
        System.out.println("sessionId=" + session.getSessionId());
        System.out.println("nameId=" + p.getNameId());
        for (Map.Entry<String, List<String>> e : p.getAttributes().entrySet()) {
            System.out.println("attr." + e.getKey() + "=" + String.join(",", e.getValue()));
        }
    }
}
