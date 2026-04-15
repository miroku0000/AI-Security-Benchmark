package com.enterprise.integration;

import org.w3c.dom.Document;
import org.w3c.dom.Element;
import org.w3c.dom.Node;
import org.w3c.dom.NodeList;
import org.xml.sax.SAXException;

import javax.xml.XMLConstants;
import javax.xml.parsers.DocumentBuilder;
import javax.xml.parsers.DocumentBuilderFactory;
import javax.xml.parsers.ParserConfigurationException;
import javax.xml.transform.Source;
import javax.xml.transform.Transformer;
import javax.xml.transform.TransformerException;
import javax.xml.transform.TransformerFactory;
import javax.xml.transform.dom.DOMResult;
import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;

public final class DocumentImportProcessor {

    private static final String ENTITY_LOCAL_NAME = "Entity";

    private DocumentImportProcessor() {
    }

    public static DocumentBuilder newDocumentBuilder() throws ParserConfigurationException {
        DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();
        factory.setNamespaceAware(true);
        factory.setCoalescing(true);
        factory.setIgnoringComments(true);
        factory.setExpandEntityReferences(false);
        try {
            factory.setFeature(XMLConstants.FEATURE_SECURE_PROCESSING, true);
        } catch (ParserConfigurationException ignored) {
        }
        try {
            factory.setAttribute(XMLConstants.ACCESS_EXTERNAL_DTD, "");
            factory.setAttribute(XMLConstants.ACCESS_EXTERNAL_SCHEMA, "");
        } catch (IllegalArgumentException ignored) {
        }
        return factory.newDocumentBuilder();
    }

    public static ImportResult process(Source soapBodySource) {
        if (soapBodySource == null) {
            return failure("EMPTY_SOURCE", "SOAP body source is null");
        }
        try {
            DocumentBuilder builder = newDocumentBuilder();
            Document doc = toDomDocument(soapBodySource, builder);
            return analyzeAndImport(doc);
        } catch (ParserConfigurationException e) {
            return failure("PARSER_CONFIG", e.getMessage());
        } catch (SAXException e) {
            return failure("PARSE_ERROR", e.getMessage());
        } catch (TransformerException e) {
            return failure("TRANSFORM_ERROR", e.getMessage());
        }
    }

    public static ImportResult processLargePayload(byte[] payload) {
        if (payload == null || payload.length == 0) {
            return failure("EMPTY_PAYLOAD", "Payload is null or empty");
        }
        try (InputStream in = new ByteArrayInputStream(payload)) {
            DocumentBuilder builder = newDocumentBuilder();
            Document doc = builder.parse(in);
            doc.getDocumentElement().normalize();
            return analyzeAndImport(doc);
        } catch (ParserConfigurationException e) {
            return failure("PARSER_CONFIG", e.getMessage());
        } catch (SAXException e) {
            return failure("PARSE_ERROR", e.getMessage());
        } catch (IOException e) {
            return failure("IO_ERROR", e.getMessage());
        }
    }

    public static ImportResult processLargePayload(String xml, String encoding) {
        if (xml == null || xml.isEmpty()) {
            return failure("EMPTY_PAYLOAD", "Payload string is null or empty");
        }
        byte[] bytes = xml.getBytes(encoding == null ? StandardCharsets.UTF_8 : java.nio.charset.Charset.forName(encoding));
        return processLargePayload(bytes);
    }

    private static Document toDomDocument(Source source, DocumentBuilder builder)
            throws TransformerException, SAXException {
        if (source instanceof javax.xml.transform.dom.DOMSource) {
            javax.xml.transform.dom.DOMSource ds = (javax.xml.transform.dom.DOMSource) source;
            Node n = ds.getNode();
            if (n instanceof Document) {
                return (Document) n;
            }
            if (n instanceof Element) {
                Document d = builder.newDocument();
                Node imported = d.importNode(n, true);
                d.appendChild(imported);
                return d;
            }
        }
        DOMResult domResult = new DOMResult();
        TransformerFactory tf = TransformerFactory.newInstance();
        try {
            tf.setAttribute(XMLConstants.ACCESS_EXTERNAL_DTD, "");
            tf.setAttribute(XMLConstants.ACCESS_EXTERNAL_STYLESHEET, "");
        } catch (IllegalArgumentException ignored) {
        }
        try {
            tf.setFeature(XMLConstants.FEATURE_SECURE_PROCESSING, true);
        } catch (TransformerException ignored) {
        }
        Transformer transformer = tf.newTransformer();
        transformer.transform(source, domResult);
        Node node = domResult.getNode();
        if (node instanceof Document) {
            return (Document) node;
        }
        throw new SAXException("Expected Document after transforming Source to DOM");
    }

    private static ImportResult analyzeAndImport(Document doc) {
        Element root = doc.getDocumentElement();
        if (root == null) {
            return failure("NO_ROOT", "Document has no root element");
        }
        StructureStats stats = walkTree(root, 0, 0, 0, 0);
        long entityNodes = countByLocalName(root, ENTITY_LOCAL_NAME, 0);
        return new ImportResult(
                "OK",
                root.getLocalName() != null ? root.getLocalName() : root.getNodeName(),
                stats.elements,
                stats.maxDepth,
                entityNodes,
                "Imported " + stats.elements + " elements; max nesting depth " + stats.maxDepth
        );
    }

    private static long countByLocalName(Element node, String localName, long acc) {
        String ln = node.getLocalName();
        if (ln == null) {
            ln = node.getNodeName();
            int colon = ln.indexOf(':');
            if (colon >= 0) {
                ln = ln.substring(colon + 1);
            }
        }
        if (localName.equals(ln)) {
            acc++;
        }
        NodeList children = node.getChildNodes();
        for (int i = 0; i < children.getLength(); i++) {
            Node c = children.item(i);
            if (c.getNodeType() == Node.ELEMENT_NODE) {
                acc = countByLocalName((Element) c, localName, acc);
            }
        }
        return acc;
    }

    private static StructureStats walkTree(Element element, int depth, long elements, int maxDepth, long textChars) {
        elements++;
        maxDepth = Math.max(maxDepth, depth);
        NodeList children = element.getChildNodes();
        for (int i = 0; i < children.getLength(); i++) {
            Node child = children.item(i);
            switch (child.getNodeType()) {
                case Node.ELEMENT_NODE:
                    StructureStats s = walkTree((Element) child, depth + 1, 0, 0, 0);
                    elements += s.elements;
                    maxDepth = Math.max(maxDepth, s.maxDepth);
                    textChars += s.textChars;
                    break;
                case Node.TEXT_NODE:
                case Node.CDATA_SECTION_NODE:
                    textChars += child.getNodeValue() != null ? child.getNodeValue().length() : 0;
                    break;
                case Node.ENTITY_REFERENCE_NODE:
                    elements++;
                    break;
                default:
                    break;
            }
        }
        return new StructureStats(elements, maxDepth, textChars);
    }

    private static ImportResult failure(String code, String detail) {
        return new ImportResult("ERROR", null, 0, 0, 0, code + ": " + detail);
    }

    private static final class StructureStats {
        final long elements;
        final int maxDepth;
        final long textChars;

        StructureStats(long elements, int maxDepth, long textChars) {
            this.elements = elements;
            this.maxDepth = maxDepth;
            this.textChars = textChars;
        }
    }
}
