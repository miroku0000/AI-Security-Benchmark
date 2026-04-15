package com.gateway.payment;

import java.time.Duration;
import java.time.Instant;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Iterator;
import java.util.List;
import java.util.Set;
import java.util.UUID;
import javax.xml.namespace.QName;
import javax.xml.soap.Node;
import javax.xml.soap.SOAPElement;
import javax.xml.soap.SOAPEnvelope;
import javax.xml.soap.SOAPException;
import javax.xml.soap.SOAPFactory;
import javax.xml.soap.SOAPHeader;
import javax.xml.soap.SOAPMessage;
import javax.xml.ws.handler.MessageContext;
import javax.xml.ws.handler.soap.SOAPHandler;
import javax.xml.ws.handler.soap.SOAPMessageContext;

public class ClientTimestampHandler implements SOAPHandler<SOAPMessageContext> {

    private static final String WSSE_NS =
            "http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd";
    private static final String WSU_NS =
            "http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd";

    private final Duration ttl;

    public ClientTimestampHandler() {
        this(Duration.ofMinutes(5));
    }

    public ClientTimestampHandler(Duration ttl) {
        this.ttl = ttl;
    }

    @Override
    public Set<QName> getHeaders() {
        return Collections.emptySet();
    }

    @Override
    public boolean handleMessage(SOAPMessageContext context) {
        Boolean outbound = (Boolean) context.get(MessageContext.MESSAGE_OUTBOUND_PROPERTY);
        if (!Boolean.TRUE.equals(outbound)) {
            return true;
        }
        try {
            SOAPMessage msg = context.getMessage();
            SOAPEnvelope env = msg.getSOAPPart().getEnvelope();
            SOAPHeader header = env.getHeader();
            if (header == null) {
                header = env.addHeader();
            }
            SOAPFactory sf = SOAPFactory.newInstance();
            removeExistingSecurity(header);
            SOAPElement security = header.addChildElement("Security", "wsse", WSSE_NS);
            String soapNs = env.getElementQName().getNamespaceURI();
            String soapPrefix = env.getPrefix();
            if (soapPrefix == null || soapPrefix.isEmpty()) {
                soapPrefix = "soap";
            }
            security.addAttribute(
                    new QName(soapNs, "mustUnderstand", soapPrefix), "1");
            Instant created = Instant.now();
            Instant expires = created.plus(ttl);
            SOAPElement ts = security.addChildElement("Timestamp", "wsu", WSU_NS);
            ts.addAttribute(new QName(WSU_NS, "Id", "wsu"), "TS-" + UUID.randomUUID());
            SOAPElement c = ts.addChildElement("Created", "wsu", WSU_NS);
            c.addTextNode(DateTimeFormatter.ISO_INSTANT.format(created));
            SOAPElement e = ts.addChildElement("Expires", "wsu", WSU_NS);
            e.addTextNode(DateTimeFormatter.ISO_INSTANT.format(expires));
            msg.saveChanges();
        } catch (SOAPException e) {
            throw new IllegalStateException(e);
        }
        return true;
    }

    private static void removeExistingSecurity(SOAPHeader header) throws SOAPException {
        List<Node> remove = new ArrayList<>();
        Iterator<?> it = header.getChildElements(new QName(WSSE_NS, "Security"));
        while (it.hasNext()) {
            remove.add((Node) it.next());
        }
        for (Node n : remove) {
            n.detach();
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
