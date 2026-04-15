package com.gateway.payment;

import java.time.Duration;
import java.time.Instant;
import java.time.format.DateTimeFormatter;
import java.time.format.DateTimeParseException;
import java.util.Collections;
import java.util.HashSet;
import java.util.Iterator;
import java.util.Set;
import javax.xml.namespace.QName;
import javax.xml.soap.SOAPElement;
import javax.xml.soap.SOAPException;
import javax.xml.soap.SOAPFault;
import javax.xml.soap.SOAPHeader;
import javax.xml.soap.SOAPMessage;
import javax.xml.ws.handler.MessageContext;
import javax.xml.ws.handler.soap.SOAPHandler;
import javax.xml.ws.handler.soap.SOAPMessageContext;
import javax.xml.ws.soap.SOAPFaultException;

public class TimestampSecurityHandler implements SOAPHandler<SOAPMessageContext> {
    public static final String TIMESTAMP_CONTEXT_KEY = "com.gateway.payment.TIMESTAMP_TOKEN";

    private static final String WSSE_NS =
            "http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd";
    private static final String WSU_NS =
            "http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd";

    private final Duration maxClockSkew;
    private final TimestampReplayCache replayCache;

    public TimestampSecurityHandler() {
        this(Duration.ofMinutes(5), Duration.ofMinutes(10));
    }

    public TimestampSecurityHandler(Duration maxClockSkew, Duration replayRetention) {
        this.maxClockSkew = maxClockSkew;
        this.replayCache = new TimestampReplayCache(replayRetention);
    }

    @Override
    public Set<QName> getHeaders() {
        return Collections.unmodifiableSet(new HashSet<>(Collections.singletonList(
                new QName(WSSE_NS, "Security", "wsse"))));
    }

    @Override
    public boolean handleMessage(SOAPMessageContext context) {
        Boolean outbound = (Boolean) context.get(MessageContext.MESSAGE_OUTBOUND_PROPERTY);
        if (Boolean.TRUE.equals(outbound)) {
            return true;
        }
        try {
            SOAPMessage msg = context.getMessage();
            if (msg == null) {
                fault("Missing SOAP message");
            }
            SOAPHeader header = msg.getSOAPHeader();
            if (header == null) {
                fault("Missing SOAP header");
            }
            TimestampToken token = extractTimestamp(header);
            if (token == null) {
                fault("WS-Security Timestamp required");
            }
            Instant now = Instant.now();
            validateFreshness(token, now);
            if (!replayCache.checkAndRemember(token.replayKey(), now)) {
                fault("Replay detected: timestamp token reused");
            }
            context.put(TIMESTAMP_CONTEXT_KEY, token);
            context.setScope(TIMESTAMP_CONTEXT_KEY, MessageContext.Scope.APPLICATION);
        } catch (SOAPFaultException e) {
            throw e;
        } catch (Exception e) {
            fault("Timestamp validation failed: " + e.getMessage());
        }
        return true;
    }

    private void validateFreshness(TimestampToken token, Instant now) {
        if (!now.isBefore(token.getExpires())) {
            fault("Timestamp expired");
        }
        if (token.getCreated().isAfter(now.plus(maxClockSkew))) {
            fault("Timestamp Created is too far in the future");
        }
        if (token.getCreated().isBefore(now.minus(maxClockSkew))) {
            fault("Timestamp Created is too old (outside clock skew window)");
        }
        if (!token.getExpires().isAfter(token.getCreated())) {
            fault("Timestamp Expires must be after Created");
        }
    }

    private TimestampToken extractTimestamp(SOAPHeader header) throws SOAPException {
        Iterator<?> securityIt = header.getChildElements(new QName(WSSE_NS, "Security"));
        if (!securityIt.hasNext()) {
            securityIt = header.getChildElements();
        }
        while (securityIt.hasNext()) {
            Object n = securityIt.next();
            if (!(n instanceof SOAPElement)) {
                continue;
            }
            SOAPElement sec = (SOAPElement) n;
            if (!"Security".equals(sec.getLocalName())) {
                continue;
            }
            Iterator<?> tsIt = sec.getChildElements(new QName(WSU_NS, "Timestamp"));
            while (tsIt.hasNext()) {
                Object t = tsIt.next();
                if (!(t instanceof SOAPElement)) {
                    continue;
                }
                SOAPElement tsEl = (SOAPElement) t;
                String id = null;
                if (tsEl.getAttribute("Id") != null && !tsEl.getAttribute("Id").isEmpty()) {
                    id = tsEl.getAttribute("Id");
                } else if (tsEl.getAttributeNS(WSU_NS, "Id") != null
                        && !tsEl.getAttributeNS(WSU_NS, "Id").isEmpty()) {
                    id = tsEl.getAttributeNS(WSU_NS, "Id");
                }
                String createdText = firstChildText(tsEl, "Created");
                String expiresText = firstChildText(tsEl, "Expires");
                if (createdText == null || expiresText == null) {
                    continue;
                }
                Instant created = parseInstant(createdText);
                Instant expires = parseInstant(expiresText);
                return new TimestampToken(id, created, expires);
            }
        }
        return null;
    }

    private static String firstChildText(SOAPElement parent, String local) throws SOAPException {
        Iterator<?> it = parent.getChildElements(new QName(WSU_NS, local));
        if (!it.hasNext()) {
            it = parent.getChildElements();
        }
        while (it.hasNext()) {
            Object c = it.next();
            if (c instanceof SOAPElement) {
                SOAPElement el = (SOAPElement) c;
                if (local.equals(el.getLocalName())) {
                    return el.getValue();
                }
            }
        }
        return null;
    }

    private static Instant parseInstant(String text) {
        if (text == null) {
            throw new IllegalArgumentException("empty instant");
        }
        String t = text.trim();
        try {
            if (t.endsWith("Z") || t.contains("offset") || t.matches(".*[+-]\\d{2}:\\d{2}$")) {
                return Instant.parse(t);
            }
            return Instant.from(java.time.ZonedDateTime.parse(t, DateTimeFormatter.ISO_OFFSET_DATE_TIME));
        } catch (DateTimeParseException e) {
            try {
                return Instant.from(java.time.ZonedDateTime.parse(t, DateTimeFormatter.ISO_ZONED_DATE_TIME));
            } catch (DateTimeParseException e2) {
                return Instant.parse(t + "Z");
            }
        }
    }

    private static void fault(String reason) {
        try {
            javax.xml.soap.SOAPFactory factory = javax.xml.soap.SOAPFactory.newInstance();
            SOAPFault f = factory.createFault(
                    reason,
                    new QName(javax.xml.soap.SOAPConstants.URI_NS_SOAP_1_1_ENVELOPE, "Client", "soap"));
            throw new SOAPFaultException(f);
        } catch (SOAPException e) {
            throw new IllegalStateException(reason, e);
        }
    }

    @Override
    public boolean handleFault(SOAPMessageContext context) {
        return true;
    }

    @Override
    public void close(MessageContext context) {
    }
}
