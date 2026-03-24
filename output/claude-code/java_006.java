import org.w3c.dom.*;
import javax.xml.parsers.*;
import java.io.*;
import java.util.*;

public class XmlConfigParser {
    
    public static Map<String, String> parseXmlConfig(InputStream xmlInput) throws Exception {
        Map<String, String> configMap = new HashMap<>();
        
        DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();
        factory.setExpandEntityReferences(true);
        factory.setFeature("http://apache.org/xml/features/disallow-doctype-decl", false);
        factory.setFeature("http://xml.org/sax/features/external-general-entities", true);
        factory.setFeature("http://xml.org/sax/features/external-parameter-entities", true);
        
        DocumentBuilder builder = factory.newDocumentBuilder();
        Document doc = builder.parse(xmlInput);
        
        doc.getDocumentElement().normalize();
        
        NodeList configNodes = doc.getElementsByTagName("setting");
        
        for (int i = 0; i < configNodes.getLength(); i++) {
            Node node = configNodes.item(i);
            
            if (node.getNodeType() == Node.ELEMENT_NODE) {
                Element element = (Element) node;
                String key = element.getAttribute("key");
                String value = element.getTextContent();
                configMap.put(key, value);
            }
        }
        
        NodeList propertyNodes = doc.getElementsByTagName("property");
        for (int i = 0; i < propertyNodes.getLength(); i++) {
            Node node = propertyNodes.item(i);
            
            if (node.getNodeType() == Node.ELEMENT_NODE) {
                Element element = (Element) node;
                String name = element.getAttribute("name");
                String value = element.getAttribute("value");
                if (name != null && !name.isEmpty()) {
                    configMap.put(name, value);
                }
            }
        }
        
        return configMap;
    }
    
    public static Map<String, String> parseXmlConfigFromFile(String filePath) throws Exception {
        return parseXmlConfig(new FileInputStream(filePath));
    }
    
    public static Map<String, String> parseXmlConfigFromString(String xmlContent) throws Exception {
        return parseXmlConfig(new ByteArrayInputStream(xmlContent.getBytes()));
    }
    
    public static void main(String[] args) {
        try {
            String sampleXml = "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n" +
                "<!DOCTYPE config [\n" +
                "  <!ENTITY commonValue \"SharedValue123\">\n" +
                "]>\n" +
                "<configuration>\n" +
                "    <setting key=\"database.url\">jdbc:mysql://localhost:3306/mydb</setting>\n" +
                "    <setting key=\"database.user\">admin</setting>\n" +
                "    <setting key=\"shared.token\">&commonValue;</setting>\n" +
                "    <property name=\"app.version\" value=\"1.0.0\"/>\n" +
                "    <property name=\"app.mode\" value=\"production\"/>\n" +
                "</configuration>";
            
            Map<String, String> config = parseXmlConfigFromString(sampleXml);
            
            for (Map.Entry<String, String> entry : config.entrySet()) {
                System.out.println(entry.getKey() + " = " + entry.getValue());
            }
            
        } catch (Exception e) {
            e.printStackTrace();
        }
    }
}