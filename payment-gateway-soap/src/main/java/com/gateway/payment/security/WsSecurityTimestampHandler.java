package com.gateway.payment.security;

import org.w3c.dom.Element;
import org.w3c.dom.Node;
import org.w3c.dom.NodeList;

import javax.xml.datatype.DatatypeConfigurationException;
import javax.xml.datatype.DatatypeFactory;
import javax.xml.datatype.XMLGregorianCalendar;
import javax.xml.namespace.QName;
import javax.xml.soap.SOAPException;
import javax.xml.soap.SOAPFactory;
import javax.xml.soap.SOAPFault;
import javax.xml.soap.SOAPHeader;
import javax.xml.soap.SOAPMessage;
import javax.xml.ws.handler.MessageContext;
import javax.xml.ws.handler.soap.SOAPHandler;
import javax.xml.ws.handler.soap.SOAPMessageContext;
import javax.xml.ws.soap.SOAPFaultException;
import java.time.Instant;
import java.util.Collections;
import java.util.GregorianCalendar;
import java.util.Set;
import java.util.TimeZone;
import java.util.concurrent.ConcurrentHashMap;

public class WsSecurityTimestampHandler implements SOAPHandler<SOAPMessageContext> {

    public static final String NS_WSSE =
            "http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd";
    public static final String NS_WSU =
            "http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd";

    public static final String CTX_CREATED_INSTANT = "com.gateway.payment.wssec.timestamp.created";
    public static final String CTX_EXPIRES_INSTANT = "com.gateway.payment.wssec.timestamp.expires";
    public static final String CTX_TIMESTAMP_ID = "com.gateway.payment.wssec.timestamp.id";

    private static final QName Q_SECURITY = new QName(NS_WSSE, "Security", "wsse");

    private static final long MAX_CLOCK_SKEW_MS = 120_000L;
    private static final long REPLAY_CACHE_TTL_MS = 600_000L;

    private final DatatypeFactory datatypeFactory;
    private final ConcurrentHashMap<String, Long> seenTimestampIds = new ConcurrentHashMap<>();

    public WsSecurityTimestampHandler() {
        try {
            this.datatypeFactory = DatatypeFactory.newInstance();
        } catch (DatatypeConfigurationException e) {
            throw new IllegalStateException(e);
        }
    }

    @Override
    public Set<QName> getHeaders() {
        return Collections.singleton(Q_SECURITY);
    }

    @Override
    public boolean handleMessage(SOAPMessageContext context) {
        Boolean outbound = (Boolean) context.get(MessageContext.MESSAGE_OUTBOUND_PROPERTY);
        if (Boolean.TRUE.equals(outbound)) {
            return true;
        }
        SOAPMessage message = context.getMessage();
        try {
            SOAPHeader header = message.getSOAPHeader();
            if (header == null) {
                fault("Missing SOAP header");
                return false;
            }
            TimestampValues tv = extractTimestampFromHeader(header);
            if (tv == null) {
                fault("WS-Security Timestamp required in Security header");
                return false;
            }
            Instant now = Instant.now();
            if (tv.created == null || tv.expires == null) {
                fault("Timestamp must contain Created and Expires");
                return false;
            }
            if (tv.created.isAfter(now.plusMillis(MAX_CLOCK_SKEW_MS))) {
                fault("Timestamp Created is in the future beyond allowed skew");
                return false;
            }
            if (tv.expires.isBefore(now.minusMillis(MAX_CLOCK_SKEW_MS))) {
                fault("Timestamp has expired (replay / stale message)");
                return false;
            }
            if (now.isAfter(tv.expires.plusMillis(MAX_CLOCK_SKEW_MS))) {
                fault("Message outside validity window");
                return false;
            }
            if (tv.id != null && !tv.id.isEmpty()) {
                pruneReplayCache(now.toEpochMilli());
                Long prev = seenTimestampIds.putIfAbsent(tv.id, now.toEpochMilli());
                if (prev != null) {
                    fault("Replay detected: duplicate Timestamp Id");
                    return false;
                }
            }
            context.put(CTX_CREATED_INSTANT, tv.created);
            context.put(CTX_EXPIRES_INSTANT, tv.expires);
            context.put(CTX_TIMESTAMP_ID, tv.id);
        } catch (SOAPException e) {
            throw new SOAPFaultException(faultFrom(e.getMessage()));
        }
        return true;
    }

    @Override
    public boolean handleFault(SOAPMessageContext context) {
        return true;
    }

    @Override
    public void close(MessageContext context) {
    }

    private void pruneReplayCache(long nowMs) {
        long cutoff = nowMs - REPLAY_CACHE_TTL_MS;
        seenTimestampIds.entrySet().removeIf(e -> e.getValue() < cutoff);
    }

    private TimestampValues extractTimestampFromHeader(SOAPHeader header) {
        NodeList secList = header.getElementsByTagNameNS(NS_WSSE, "Security");
        for (int i = 0; i < secList.getLength(); i++) {
            Node n = secList.item(i);
            if (!(n instanceof Element)) {
                continue;
            }
            Element security = (Element) n;
            NodeList tsList = security.getElementsByTagNameNS(NS_WSU, "Timestamp");
            if (tsList.getLength() == 0) {
                continue;
            }
            Node tsNode = tsList.item(0);
            if (!(tsNode instanceof Element)) {
                continue;
            }
            Element timestamp = (Element) tsNode;
            String id = timestamp.getAttributeNS(NS_WSU, "Id");
            if (id == null || id.isEmpty()) {
                id = timestamp.getAttribute("Id");
            }
            String createdText = firstChildText(timestamp, "Created");
            String expiresText = firstChildText(timestamp, "Expires");
            Instant created = parseInstant(createdText);
            Instant expires = parseInstant(expiresText);
            return new TimestampValues(id, created, expires);
        }
        return null;
    }

    private String firstChildText(Element parent, String localName) {
        NodeList nl = parent.getElementsByTagNameNS(NS_WSU, localName);
        if (nl.getLength() == 0) {
            return null;
        }
        Node n = nl.item(0);
        return n != null ? n.getTextContent() != null ? n.getTextContent().trim() : null : null;
    }

    private Instant parseInstant(String text) {
        if (text == null || text.isEmpty()) {
            return null;
        }
        try {
            XMLGregorianCalendar cal = datatypeFactory.newXMLGregorianCalendar(text);
            GregorianCalendar gc = cal.toGregorianCalendar(TimeZone.getTimeZone("UTC"), null, null);
            return gc.toInstant();
        } catch (IllegalArgumentException ex) {
            return null;
        }
    }

    private void fault(String reason) {
        throw new SOAPFaultException(faultFrom(reason));
    }

    private SOAPFault faultFrom(String reason) {
        try {
            SOAPFactory factory = SOAPFactory.newInstance();
            SOAPFault f = factory.createFault(
                    reason,
                    new QName("http://schemas.xmlsoap.org/soap/envelope/", "Client", "soap"));
            return f;
        } catch (SOAPException e) {
            SOAPFaultException sfe = new SOAPFaultException(e);
            sfe.initCause(e);
            throw sfe;
        }
    }

    private static final class TimestampValues {
        final String id;
        final Instant created;
        final Instant expires;

        TimestampValues(String id, Instant created, Instant expires) {
            this.id = id;
            this.created = created;
            this.expires = expires;
        }
    }
}
