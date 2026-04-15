import java.io.InputStream;
import java.util.HashMap;
import java.util.Map;

import javax.xml.XMLConstants;
import javax.xml.parsers.DocumentBuilder;
import javax.xml.parsers.DocumentBuilderFactory;

import org.w3c.dom.Document;
import org.w3c.dom.Element;
import org.w3c.dom.Node;
import org.w3c.dom.NodeList;
import org.w3c.dom.Text;

public final class UserXmlConfigurationParser {

    private UserXmlConfigurationParser() {
    }

    public static Map<String, String> parseConfiguration(InputStream xmlStream) throws Exception {
        DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();
        factory.setNamespaceAware(true);
        factory.setFeature(XMLConstants.FEATURE_SECURE_PROCESSING, true);
        factory.setFeature("http://apache.org/xml/features/disallow-doctype-decl", false);
        factory.setFeature("http://xml.org/sax/features/external-general-entities", false);
        factory.setFeature("http://xml.org/sax/features/external-parameter-entities", false);
        factory.setXIncludeAware(false);
        factory.setExpandEntityReferences(true);

        DocumentBuilder builder = factory.newDocumentBuilder();
        Document document = builder.parse(xmlStream);
        Element root = document.getDocumentElement();

        Map<String, String> settings = new HashMap<>();
        NodeList children = root.getChildNodes();
        for (int i = 0; i < children.getLength(); i++) {
            Node child = children.item(i);
            if (child.getNodeType() == Node.ELEMENT_NODE) {
                Element element = (Element) child;
                String key = element.getTagName();
                String value = collectTextContent(element).trim();
                settings.put(key, value);
            }
        }
        return settings;
    }

    private static String collectTextContent(Element element) {
        StringBuilder sb = new StringBuilder();
        NodeList nodes = element.getChildNodes();
        for (int i = 0; i < nodes.getLength(); i++) {
            Node n = nodes.item(i);
            if (n.getNodeType() == Node.TEXT_NODE || n.getNodeType() == Node.CDATA_SECTION_NODE) {
                sb.append(n.getNodeValue());
            } else if (n.getNodeType() == Node.ENTITY_REFERENCE_NODE) {
                for (Node c = n.getFirstChild(); c != null; c = c.getNextSibling()) {
                    if (c.getNodeType() == Node.TEXT_NODE) {
                        sb.append(((Text) c).getData());
                    }
                }
            }
        }
        return sb.toString();
    }
}