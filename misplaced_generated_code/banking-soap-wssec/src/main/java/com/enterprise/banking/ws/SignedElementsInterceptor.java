package com.enterprise.banking.ws;

import org.apache.cxf.binding.soap.SoapMessage;
import org.apache.cxf.interceptor.Fault;
import org.apache.cxf.phase.AbstractPhaseInterceptor;
import org.apache.cxf.phase.Phase;
import org.apache.wss4j.dom.WSDataRef;
import org.apache.wss4j.dom.engine.WSSecurityEngineResult;
import org.apache.wss4j.dom.handler.WSHandlerConstants;
import org.apache.wss4j.dom.handler.WSHandlerResult;
import org.w3c.dom.Document;
import org.w3c.dom.Element;
import org.w3c.dom.Node;
import org.w3c.dom.NodeList;

import javax.xml.namespace.QName;
import javax.xml.soap.SOAPBody;
import javax.xml.soap.SOAPException;
import javax.xml.soap.SOAPHeader;
import javax.xml.soap.SOAPMessage;
import javax.xml.soap.SOAPPart;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

public class SignedElementsInterceptor extends AbstractPhaseInterceptor<SoapMessage> {

    public static final String SIGNED_QNAMES = SignedElementsInterceptor.class.getName() + ".signedQNames";

    public SignedElementsInterceptor() {
        super(Phase.PRE_INVOKE);
    }

    @Override
    public void handleMessage(SoapMessage message) throws Fault {
        List<QName> signed = extractSignedElementQNames(message);
        message.put(SIGNED_QNAMES, signed);
        if (!signed.isEmpty()) {
            message.getExchange().put(SIGNED_QNAMES, signed);
        }
    }

    @SuppressWarnings("unchecked")
    public static List<QName> extractSignedElementQNames(SoapMessage message) {
        Object raw = message.get(WSHandlerConstants.RECV_RESULTS);
        if (!(raw instanceof List)) {
            return Collections.emptyList();
        }
        List<WSHandlerResult> handlerResults = (List<WSHandlerResult>) raw;
        List<String> ids = new ArrayList<>();
        for (WSHandlerResult hr : handlerResults) {
            for (WSSecurityEngineResult er : hr.getResults()) {
                Object action = er.get(WSSecurityEngineResult.TAG_ACTION);
                if (action instanceof Integer && (Integer) action == WSSecurityEngineResult.SIGNATURE) {
                    Object refUris = er.get(WSSecurityEngineResult.TAG_DATA_REF_URIS);
                    if (refUris instanceof List) {
                        for (Object o : (List<?>) refUris) {
                            if (o instanceof WSDataRef) {
                                WSDataRef dr = (WSDataRef) o;
                                if (dr.getWsuId() != null) {
                                    ids.add(dr.getWsuId());
                                } else if (dr.getUri() != null) {
                                    ids.add(dr.getUri());
                                }
                            } else if (o != null) {
                                ids.add(o.toString());
                            }
                        }
                    }
                }
            }
        }
        if (ids.isEmpty()) {
            return Collections.emptyList();
        }
        SOAPMessage soapMessage;
        try {
            soapMessage = message.getContent(SOAPMessage.class);
        } catch (Exception e) {
            throw new Fault(e);
        }
        if (soapMessage == null) {
            return Collections.emptyList();
        }
        List<QName> out = new ArrayList<>();
        try {
            SOAPPart part = soapMessage.getSOAPPart();
            Document doc = part.getEnvelope().getOwnerDocument();
            for (String id : ids) {
                String localId = stripUriFragment(id);
                Element el = findElementByWsuId(doc, localId);
                if (el == null) {
                    el = findElementById(doc, localId);
                }
                if (el != null) {
                    out.add(new QName(el.getNamespaceURI(), el.getLocalName()));
                }
            }
        } catch (SOAPException e) {
            throw new Fault(e);
        }
        return out;
    }

    private static String stripUriFragment(String id) {
        if (id == null) {
            return "";
        }
        int h = id.indexOf('#');
        return h >= 0 ? id.substring(h + 1) : id;
    }

    private static Element findElementByWsuId(Document doc, String id) {
        if (id == null || id.isEmpty()) {
            return null;
        }
        NodeList all = doc.getElementsByTagNameNS("*", "*");
        for (int i = 0; i < all.getLength(); i++) {
            Node n = all.item(i);
            if (n instanceof Element) {
                Element e = (Element) n;
                String wsuId = e.getAttributeNS("http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd", "Id");
                if (id.equals(wsuId)) {
                    return e;
                }
            }
        }
        return null;
    }

    private static Element findElementById(Document doc, String id) {
        if (id == null || id.isEmpty()) {
            return null;
        }
        NodeList all = doc.getElementsByTagNameNS("*", "*");
        for (int i = 0; i < all.getLength(); i++) {
            Node n = all.item(i);
            if (n instanceof Element) {
                Element e = (Element) n;
                if (id.equals(e.getAttribute("Id"))) {
                    return e;
                }
            }
        }
        return null;
    }

    public static void attachSignedSummary(SoapMessage message) {
        List<QName> q = extractSignedElementQNames(message);
        message.put(SIGNED_QNAMES, q);
    }

    public static List<QName> bodyHeaderChildQNames(SOAPMessage sm) throws SOAPException {
        List<QName> q = new ArrayList<>();
        SOAPEnvelope env = sm.getSOAPPart().getEnvelope();
        SOAPBody b = env.getBody();
        if (b != null) {
            q.add(new QName(b.getNamespaceURI(), b.getLocalName()));
            NodeList nl = b.getChildNodes();
            for (int i = 0; i < nl.getLength(); i++) {
                if (nl.item(i) instanceof Element) {
                    Element e = (Element) nl.item(i);
                    q.add(new QName(e.getNamespaceURI(), e.getLocalName()));
                }
            }
        }
        SOAPHeader h = env.getHeader();
        if (h != null) {
            q.add(new QName(h.getNamespaceURI(), h.getLocalName()));
        }
        return q;
    }
}
