package com.enterprise.integration;

import org.w3c.dom.Node;

import javax.xml.soap.SOAPBody;
import javax.xml.soap.SOAPException;
import javax.xml.soap.SOAPMessage;
import javax.xml.transform.Source;
import javax.xml.transform.dom.DOMSource;
import javax.xml.ws.WebServiceContext;
import javax.xml.ws.handler.MessageContext;
import javax.xml.ws.soap.SOAPMessageContext;

public final class SoapBodySources {

    private SoapBodySources() {
    }

    public static Source firstPayloadSource(WebServiceContext ctx) {
        if (ctx == null) {
            return null;
        }
        MessageContext mc = ctx.getMessageContext();
        if (!(mc instanceof SOAPMessageContext)) {
            return null;
        }
        SOAPMessageContext smc = (SOAPMessageContext) mc;
        try {
            SOAPMessage message = smc.getMessage();
            if (message == null) {
                return null;
            }
            SOAPBody body = message.getSOAPBody();
            if (body == null) {
                return null;
            }
            Node first = body.getFirstChild();
            while (first != null && first.getNodeType() != Node.ELEMENT_NODE) {
                first = first.getNextSibling();
            }
            if (first == null) {
                return new DOMSource(body);
            }
            return new DOMSource(first);
        } catch (SOAPException e) {
            return null;
        }
    }
}
