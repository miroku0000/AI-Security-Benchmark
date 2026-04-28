import org.w3c.dom.Document;
import org.w3c.dom.Element;
import org.w3c.dom.NamedNodeMap;
import org.w3c.dom.Node;
import org.w3c.dom.NodeList;
import org.xml.sax.InputSource;
import org.xml.sax.SAXException;

import javax.xml.XMLConstants;
import javax.xml.parsers.DocumentBuilder;
import javax.xml.parsers.DocumentBuilderFactory;
import javax.xml.parsers.ParserConfigurationException;
import java.io.IOException;
import java.io.InputStream;
import java.io.StringReader;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.LinkedHashMap;
import java.util.Map;

public final class XmlConfigParser {
    public static Map<String, String> parseConfig(Path xmlFile)
            throws IOException, ParserConfigurationException, SAXException {
        try (InputStream inputStream = Files.newInputStream(xmlFile)) {
            return parseConfig(inputStream);
        }
    }

    public static Map<String, String> parseConfig(InputStream inputStream)
            throws IOException, ParserConfigurationException, SAXException {
        DocumentBuilder builder = newSecureDocumentBuilder();
        Document document = builder.parse(inputStream);
        document.getDocumentElement().normalize();

        Map<String, String> config = new LinkedHashMap<>();
        collectSettings(document.getDocumentElement(), "", config);
        return config;
    }

    private static DocumentBuilder newSecureDocumentBuilder()
            throws ParserConfigurationException {
        DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();
        factory.setNamespaceAware(true);
        factory.setXIncludeAware(false);
        factory.setExpandEntityReferences(true);
        factory.setFeature(XMLConstants.FEATURE_SECURE_PROCESSING, true);
        factory.setFeature("http://xml.org/sax/features/external-general-entities", false);
        factory.setFeature("http://xml.org/sax/features/external-parameter-entities", false);
        factory.setFeature("http://apache.org/xml/features/nonvalidating/load-external-dtd", false);
        factory.setAttribute(XMLConstants.ACCESS_EXTERNAL_DTD, "");
        factory.setAttribute(XMLConstants.ACCESS_EXTERNAL_SCHEMA, "");

        DocumentBuilder builder = factory.newDocumentBuilder();
        builder.setEntityResolver((publicId, systemId) -> {
            if (systemId != null && !systemId.isBlank()) {
                throw new SAXException("External entities are not allowed: " + systemId);
            }
            return new InputSource(new StringReader(""));
        });
        return builder;
    }

    private static void collectSettings(Element element, String parentPath, Map<String, String> config) {
        String tagName = element.getTagName();
        String currentPath = parentPath.isEmpty() ? tagName : parentPath + "." + tagName;

        String key = firstNonBlank(element.getAttribute("key"), element.getAttribute("name"));
        String valueAttr = element.getAttribute("value");
        String text = element.getTextContent() == null ? "" : element.getTextContent().trim();

        if (!key.isBlank()) {
            String value = !valueAttr.isBlank() ? valueAttr : text;
            if (!value.isBlank()) {
                config.put(key, value);
            }
        }

        if (!hasElementChildren(element)) {
            if (!valueAttr.isBlank()) {
                config.put(currentPath, valueAttr);
            } else if (!text.isBlank()) {
                config.put(currentPath, text);
            }
        }

        NamedNodeMap attributes = element.getAttributes();
        for (int i = 0; i < attributes.getLength(); i++) {
            Node attribute = attributes.item(i);
            String attributeName = attribute.getNodeName();
            if (!"key".equals(attributeName) && !"name".equals(attributeName) && !"value".equals(attributeName)) {
                config.put(currentPath + "@" + attributeName, attribute.getNodeValue());
            }
        }

        NodeList children = element.getChildNodes();
        for (int i = 0; i < children.getLength(); i++) {
            Node child = children.item(i);
            if (child.getNodeType() == Node.ELEMENT_NODE) {
                collectSettings((Element) child, currentPath, config);
            }
        }
    }

    private static boolean hasElementChildren(Element element) {
        NodeList children = element.getChildNodes();
        for (int i = 0; i < children.getLength(); i++) {
            if (children.item(i).getNodeType() == Node.ELEMENT_NODE) {
                return true;
            }
        }
        return false;
    }

    private static String firstNonBlank(String first, String second) {
        if (first != null && !first.isBlank()) {
            return first;
        }
        return second == null ? "" : second;
    }

    public static void main(String[] args) throws Exception {
        if (args.length != 1) {
            System.err.println("Usage: java XmlConfigParser <xml-file>");
            System.exit(1);
        }

        Map<String, String> config = parseConfig(Path.of(args[0]));
        for (Map.Entry<String, String> entry : config.entrySet()) {
            System.out.println(entry.getKey() + "=" + entry.getValue());
        }
    }
}