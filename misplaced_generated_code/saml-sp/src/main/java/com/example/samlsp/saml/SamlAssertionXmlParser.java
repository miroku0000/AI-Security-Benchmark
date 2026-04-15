package com.example.samlsp.saml;

import java.io.StringReader;
import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import javax.xml.XMLConstants;
import javax.xml.parsers.DocumentBuilderFactory;
import org.w3c.dom.Document;
import org.w3c.dom.Element;
import org.w3c.dom.Node;
import org.w3c.dom.NodeList;
import org.xml.sax.InputSource;

public final class SamlAssertionXmlParser {
  private SamlAssertionXmlParser() {}

  public static String extractAssertionId(String samlResponseXml) {
    try {
      Document doc = parse(samlResponseXml);
      Element assertion = firstElementByLocalName(doc.getDocumentElement(), "Assertion");
      if (assertion == null) {
        return null;
      }
      return assertion.getAttribute("ID");
    } catch (Exception e) {
      throw new SamlException("Failed to extract Assertion ID from SAML XML", e);
    }
  }

  public static Map<String, List<String>> extractAttributes(String samlResponseXml) {
    try {
      Document doc = parse(samlResponseXml);
      Element assertion = firstElementByLocalName(doc.getDocumentElement(), "Assertion");
      if (assertion == null) {
        return Map.of();
      }
      Element attrStatement = firstElementByLocalName(assertion, "AttributeStatement");
      if (attrStatement == null) {
        return Map.of();
      }
      Map<String, List<String>> out = new LinkedHashMap<>();
      for (Element attrEl : childElementsByLocalName(attrStatement, "Attribute")) {
        String name = attrEl.getAttribute("Name");
        if (name == null || name.isBlank()) {
          continue;
        }
        List<String> values = new ArrayList<>();
        for (Element av : childElementsByLocalName(attrEl, "AttributeValue")) {
          String v = av.getTextContent();
          if (v != null) {
            v = v.trim();
            if (!v.isEmpty()) {
              values.add(v);
            }
          }
        }
        if (!values.isEmpty()) {
          out.put(name, Collections.unmodifiableList(new ArrayList<>(values)));
        }
      }
      return Collections.unmodifiableMap(out);
    } catch (SamlException e) {
      throw e;
    } catch (Exception e) {
      throw new SamlException("Failed to extract attributes from SAML assertion XML", e);
    }
  }

  private static Document parse(String xml) throws Exception {
    DocumentBuilderFactory dbf = DocumentBuilderFactory.newInstance();
    dbf.setNamespaceAware(true);
    dbf.setFeature(XMLConstants.FEATURE_SECURE_PROCESSING, true);
    dbf.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
    dbf.setFeature("http://xml.org/sax/features/external-general-entities", false);
    dbf.setFeature("http://xml.org/sax/features/external-parameter-entities", false);
    dbf.setFeature("http://apache.org/xml/features/nonvalidating/load-external-dtd", false);
    dbf.setXIncludeAware(false);
    dbf.setExpandEntityReferences(false);
    return dbf.newDocumentBuilder().parse(new InputSource(new StringReader(xml)));
  }

  private static Element firstElementByLocalName(Element root, String localName) {
    if (root == null) {
      return null;
    }
    if (localName.equals(root.getLocalName())) {
      return root;
    }
    NodeList children = root.getChildNodes();
    for (int i = 0; i < children.getLength(); i++) {
      Node n = children.item(i);
      if (n.getNodeType() == Node.ELEMENT_NODE) {
        Element el = (Element) n;
        if (localName.equals(el.getLocalName())) {
          return el;
        }
        Element found = firstElementByLocalName(el, localName);
        if (found != null) {
          return found;
        }
      }
    }
    return null;
  }

  private static List<Element> childElementsByLocalName(Element parent, String localName) {
    List<Element> list = new ArrayList<>();
    NodeList children = parent.getChildNodes();
    for (int i = 0; i < children.getLength(); i++) {
      Node n = children.item(i);
      if (n.getNodeType() == Node.ELEMENT_NODE) {
        Element el = (Element) n;
        if (localName.equals(el.getLocalName())) {
          list.add(el);
        }
      }
    }
    return list;
  }
}
