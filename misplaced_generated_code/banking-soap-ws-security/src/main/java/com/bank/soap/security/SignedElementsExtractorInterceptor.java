package com.bank.soap.security;

import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Deque;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import javax.xml.soap.SOAPBody;
import javax.xml.soap.SOAPEnvelope;
import javax.xml.soap.SOAPMessage;
import org.apache.cxf.binding.soap.SoapMessage;
import org.apache.cxf.interceptor.Fault;
import org.apache.cxf.phase.AbstractPhaseInterceptor;
import org.apache.cxf.phase.Phase;
import org.w3c.dom.Attr;
import org.w3c.dom.Element;
import org.w3c.dom.NamedNodeMap;
import org.w3c.dom.Node;
import org.w3c.dom.NodeList;

public class SignedElementsExtractorInterceptor extends AbstractPhaseInterceptor<SoapMessage> {
  public static final String SIGNED_ELEMENTS_KEY = "com.bank.soap.signedElements";
  public static final String SIGNED_ELEMENT_IDS_KEY = "com.bank.soap.signedElementIds";

  private static final String NS_WSSE = "http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd";
  private static final String NS_WSU = "http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd";
  private static final String NS_DS = "http://www.w3.org/2000/09/xmldsig#";

  public SignedElementsExtractorInterceptor() {
    super(Phase.PRE_INVOKE);
  }

  @Override
  public void handleMessage(SoapMessage message) throws Fault {
    try {
      SOAPMessage soap = message.getContent(SOAPMessage.class);
      if (soap == null) {
        message.put(SIGNED_ELEMENTS_KEY, List.of());
        message.put(SIGNED_ELEMENT_IDS_KEY, List.of());
        return;
      }

      SOAPEnvelope env = soap.getSOAPPart().getEnvelope();
      SOAPBody body = env.getBody();

      Element envelopeEl = env;
      if (envelopeEl == null) {
        message.put(SIGNED_ELEMENTS_KEY, List.of());
        message.put(SIGNED_ELEMENT_IDS_KEY, List.of());
        return;
      }

      Set<String> referencedIds = extractSignatureReferenceIds(envelopeEl);
      if (referencedIds.isEmpty()) {
        message.put(SIGNED_ELEMENTS_KEY, List.of());
        message.put(SIGNED_ELEMENT_IDS_KEY, List.of());
        return;
      }

      List<Element> signedElements = new ArrayList<>();
      for (String id : referencedIds) {
        Element el = findElementById(envelopeEl, id);
        if (el != null) {
          signedElements.add(el);
        }
      }

      if (body != null) {
        tryEnsureWsuIdRecognized((Element) body, referencedIds);
      }

      message.put(SIGNED_ELEMENTS_KEY, signedElements);
      message.put(SIGNED_ELEMENT_IDS_KEY, new ArrayList<>(referencedIds));
    } catch (Exception e) {
      throw new Fault(e);
    }
  }

  private static Set<String> extractSignatureReferenceIds(Element envelopeEl) {
    Set<String> ids = new HashSet<>();

    NodeList securityHeaders = envelopeEl.getElementsByTagNameNS(NS_WSSE, "Security");
    for (int i = 0; i < securityHeaders.getLength(); i++) {
      Node sh = securityHeaders.item(i);
      if (!(sh instanceof Element)) continue;
      Element sec = (Element) sh;

      NodeList signatures = sec.getElementsByTagNameNS(NS_DS, "Signature");
      for (int s = 0; s < signatures.getLength(); s++) {
        Node sig = signatures.item(s);
        if (!(sig instanceof Element)) continue;
        Element sigEl = (Element) sig;

        NodeList refs = sigEl.getElementsByTagNameNS(NS_DS, "Reference");
        for (int r = 0; r < refs.getLength(); r++) {
          Node ref = refs.item(r);
          if (!(ref instanceof Element)) continue;
          Element refEl = (Element) ref;
          String uri = refEl.getAttribute("URI");
          if (uri == null) continue;
          uri = uri.trim();
          if (uri.startsWith("#") && uri.length() > 1) {
            ids.add(uri.substring(1));
          }
        }
      }
    }
    return ids;
  }

  private static Element findElementById(Element root, String id) {
    Deque<Node> stack = new ArrayDeque<>();
    stack.push(root);
    while (!stack.isEmpty()) {
      Node n = stack.pop();
      if (n instanceof Element) {
        Element e = (Element) n;
        if (idEquals(e, id)) {
          return e;
        }
      }

      Node child = n.getLastChild();
      while (child != null) {
        stack.push(child);
        child = child.getPreviousSibling();
      }
    }
    return null;
  }

  private static boolean idEquals(Element e, String id) {
    if (id.equals(e.getAttributeNS(NS_WSU, "Id"))) return true;
    if (id.equals(e.getAttribute("Id"))) return true;
    if (id.equals(e.getAttribute("ID"))) return true;
    if (id.equals(e.getAttribute("id"))) return true;

    NamedNodeMap attrs = e.getAttributes();
    if (attrs == null) return false;
    for (int i = 0; i < attrs.getLength(); i++) {
      Node a = attrs.item(i);
      if (a instanceof Attr) {
        Attr at = (Attr) a;
        String local = at.getLocalName();
        String ns = at.getNamespaceURI();
        if ("Id".equals(local) && NS_WSU.equals(ns) && id.equals(at.getValue())) return true;
      }
    }
    return false;
  }

  private static void tryEnsureWsuIdRecognized(Element element, Set<String> ids) {
    if (element == null) return;
    for (String id : ids) {
      if (id.equals(element.getAttributeNS(NS_WSU, "Id"))) {
        element.setIdAttributeNS(NS_WSU, "Id", true);
      }
    }
  }
}

