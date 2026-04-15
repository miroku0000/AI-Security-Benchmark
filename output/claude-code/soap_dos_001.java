import javax.xml.parsers.DocumentBuilder;
import javax.xml.parsers.DocumentBuilderFactory;
import javax.xml.soap.*;
import javax.xml.transform.*;
import javax.xml.transform.dom.DOMSource;
import javax.xml.transform.stream.StreamResult;
import org.w3c.dom.*;
import org.xml.sax.InputSource;
import java.io.*;
import java.net.*;
import java.util.*;
import java.util.concurrent.*;
import com.sun.net.httpserver.HttpServer;
import com.sun.net.httpserver.HttpHandler;
import com.sun.net.httpserver.HttpExchange;

public class SoapDataIntegrationService {

    private static final int MAX_PAYLOAD_SIZE = 10 * 1024 * 1024; // 10 MB
    private static final int PORT = 8080;
    private final ExecutorService executor = Executors.newFixedThreadPool(10);
    private final Map<String, List<Map<String, String>>> dataStore = new ConcurrentHashMap<>();

    public static void main(String[] args) throws Exception {
        SoapDataIntegrationService service = new SoapDataIntegrationService();
        service.start();
    }

    public void start() throws Exception {
        HttpServer server = HttpServer.create(new InetSocketAddress(PORT), 0);
        server.createContext("/soap/data-integration", new SoapHandler());
        server.setExecutor(executor);
        server.start();
        System.out.println("SOAP Data Integration Service running on port " + PORT);
    }

    private DocumentBuilder createSecureDocumentBuilder() throws Exception {
        DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();
        factory.setNamespaceAware(true);

        // Disable external entities and DTDs to prevent XXE attacks
        factory.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
        factory.setFeature("http://xml.org/sax/features/external-general-entities", false);
        factory.setFeature("http://xml.org/sax/features/external-parameter-entities", false);
        factory.setFeature("http://apache.org/xml/features/nonvalidating/load-external-dtd", false);
        factory.setXIncludeAware(false);
        factory.setExpandEntityReferences(false);

        return factory.newDocumentBuilder();
    }

    private class SoapHandler implements HttpHandler {
        @Override
        public void handle(HttpExchange exchange) throws IOException {
            if (!"POST".equalsIgnoreCase(exchange.getRequestMethod())) {
                sendSoapFault(exchange, "Client", "Only POST method is supported", 405);
                return;
            }

            String contentType = exchange.getRequestHeaders().getFirst("Content-Type");
            if (contentType == null || (!contentType.contains("text/xml") && !contentType.contains("application/soap+xml"))) {
                sendSoapFault(exchange, "Client", "Content-Type must be text/xml or application/soap+xml", 415);
                return;
            }

            byte[] requestBytes;
            try (InputStream is = exchange.getRequestBody()) {
                ByteArrayOutputStream buffer = new ByteArrayOutputStream();
                byte[] chunk = new byte[8192];
                int bytesRead;
                int totalRead = 0;
                while ((bytesRead = is.read(chunk)) != -1) {
                    totalRead += bytesRead;
                    if (totalRead > MAX_PAYLOAD_SIZE) {
                        sendSoapFault(exchange, "Client", "Payload exceeds maximum size of " + MAX_PAYLOAD_SIZE + " bytes", 413);
                        return;
                    }
                    buffer.write(chunk, 0, bytesRead);
                }
                requestBytes = buffer.toByteArray();
            }

            try {
                DocumentBuilder builder = createSecureDocumentBuilder();
                Document doc = builder.parse(new InputSource(new ByteArrayInputStream(requestBytes)));
                doc.getDocumentElement().normalize();

                String operation = extractOperation(doc);
                String responseXml;

                switch (operation) {
                    case "ImportData":
                        responseXml = handleImportData(doc);
                        break;
                    case "QueryData":
                        responseXml = handleQueryData(doc);
                        break;
                    case "BatchImport":
                        responseXml = handleBatchImport(doc);
                        break;
                    case "GetStatus":
                        responseXml = handleGetStatus();
                        break;
                    default:
                        sendSoapFault(exchange, "Client", "Unknown operation: " + operation, 400);
                        return;
                }

                byte[] responseBytes = responseXml.getBytes("UTF-8");
                exchange.getResponseHeaders().set("Content-Type", "text/xml; charset=utf-8");
                exchange.sendResponseHeaders(200, responseBytes.length);
                try (OutputStream os = exchange.getResponseBody()) {
                    os.write(responseBytes);
                }

            } catch (Exception e) {
                sendSoapFault(exchange, "Server", "Processing error: " + e.getMessage(), 500);
            }
        }
    }

    private String extractOperation(Document doc) {
        Element body = getFirstChildElement(doc.getDocumentElement(), "Body");
        if (body == null) {
            NodeList bodyList = doc.getElementsByTagNameNS("http://schemas.xmlsoap.org/soap/envelope/", "Body");
            if (bodyList.getLength() == 0) {
                bodyList = doc.getElementsByTagNameNS("http://www.w3.org/2003/05/soap-envelope", "Body");
            }
            if (bodyList.getLength() > 0) {
                body = (Element) bodyList.item(0);
            }
        }

        if (body == null) {
            return "Unknown";
        }

        NodeList children = body.getChildNodes();
        for (int i = 0; i < children.getLength(); i++) {
            if (children.item(i) instanceof Element) {
                String localName = children.item(i).getLocalName();
                if (localName == null) {
                    localName = children.item(i).getNodeName();
                    if (localName.contains(":")) {
                        localName = localName.substring(localName.indexOf(':') + 1);
                    }
                }
                return localName;
            }
        }
        return "Unknown";
    }

    private String handleImportData(Document doc) throws Exception {
        Element body = getSoapBody(doc);
        Element importElement = getFirstChildElement(body);
        if (importElement == null) {
            return buildSoapResponse("<ImportDataResponse><Status>Error</Status><Message>No import data found</Message></ImportDataResponse>");
        }

        String dataset = getElementText(importElement, "DatasetName");
        if (dataset == null || dataset.isEmpty()) {
            dataset = "default";
        }

        Element records = getFirstChildElement(importElement, "Records");
        int count = 0;

        if (records != null) {
            NodeList recordList = records.getChildNodes();
            List<Map<String, String>> dataList = dataStore.computeIfAbsent(dataset, k -> new CopyOnWriteArrayList<>());

            for (int i = 0; i < recordList.getLength(); i++) {
                if (recordList.item(i) instanceof Element) {
                    Element record = (Element) recordList.item(i);
                    Map<String, String> row = new LinkedHashMap<>();
                    parseNestedElement(record, "", row);
                    dataList.add(row);
                    count++;
                }
            }
        }

        return buildSoapResponse(
            "<ImportDataResponse>" +
            "<Status>Success</Status>" +
            "<RecordsImported>" + count + "</RecordsImported>" +
            "<Dataset>" + escapeXml(dataset) + "</Dataset>" +
            "</ImportDataResponse>"
        );
    }

    private String handleBatchImport(Document doc) throws Exception {
        Element body = getSoapBody(doc);
        Element batchElement = getFirstChildElement(body);
        if (batchElement == null) {
            return buildSoapResponse("<BatchImportResponse><Status>Error</Status></BatchImportResponse>");
        }

        int totalImported = 0;
        int batchCount = 0;
        StringBuilder details = new StringBuilder();

        NodeList batches = batchElement.getChildNodes();
        for (int i = 0; i < batches.getLength(); i++) {
            if (batches.item(i) instanceof Element) {
                Element batch = (Element) batches.item(i);
                String batchName = batch.getLocalName() != null ? batch.getLocalName() : batch.getNodeName();
                if ("Batch".equals(batchName) || batchName.endsWith(":Batch")) {
                    String dataset = getElementText(batch, "DatasetName");
                    if (dataset == null) dataset = "batch_" + batchCount;

                    Element records = getFirstChildElement(batch, "Records");
                    int count = 0;
                    if (records != null) {
                        List<Map<String, String>> dataList = dataStore.computeIfAbsent(dataset, k -> new CopyOnWriteArrayList<>());
                        NodeList recordList = records.getChildNodes();
                        for (int j = 0; j < recordList.getLength(); j++) {
                            if (recordList.item(j) instanceof Element) {
                                Map<String, String> row = new LinkedHashMap<>();
                                parseNestedElement((Element) recordList.item(j), "", row);
                                dataList.add(row);
                                count++;
                            }
                        }
                    }
                    totalImported += count;
                    batchCount++;
                    details.append("<BatchResult><Dataset>").append(escapeXml(dataset))
                           .append("</Dataset><Count>").append(count).append("</Count></BatchResult>");
                }
            }
        }

        return buildSoapResponse(
            "<BatchImportResponse>" +
            "<Status>Success</Status>" +
            "<TotalRecords>" + totalImported + "</TotalRecords>" +
            "<BatchesProcessed>" + batchCount + "</BatchesProcessed>" +
            "<Details>" + details + "</Details>" +
            "</BatchImportResponse>"
        );
    }

    private String handleQueryData(Document doc) throws Exception {
        Element body = getSoapBody(doc);
        Element queryElement = getFirstChildElement(body);

        String dataset = getElementText(queryElement, "DatasetName");
        if (dataset == null) dataset = "default";

        String filterField = getElementText(queryElement, "FilterField");
        String filterValue = getElementText(queryElement, "FilterValue");

        List<Map<String, String>> data = dataStore.getOrDefault(dataset, Collections.emptyList());
        StringBuilder results = new StringBuilder();
        int matchCount = 0;

        for (Map<String, String> row : data) {
            if (filterField == null || filterValue == null || filterValue.equals(row.get(filterField))) {
                results.append("<Record>");
                for (Map.Entry<String, String> entry : row.entrySet()) {
                    String safeKey = entry.getKey().replaceAll("[^a-zA-Z0-9_]", "_");
                    results.append("<").append(safeKey).append(">")
                           .append(escapeXml(entry.getValue()))
                           .append("</").append(safeKey).append(">");
                }
                results.append("</Record>");
                matchCount++;
            }
        }

        return buildSoapResponse(
            "<QueryDataResponse>" +
            "<Status>Success</Status>" +
            "<Dataset>" + escapeXml(dataset) + "</Dataset>" +
            "<MatchCount>" + matchCount + "</MatchCount>" +
            "<Records>" + results + "</Records>" +
            "</QueryDataResponse>"
        );
    }

    private String handleGetStatus() {
        StringBuilder datasets = new StringBuilder();
        for (Map.Entry<String, List<Map<String, String>>> entry : dataStore.entrySet()) {
            datasets.append("<Dataset><Name>").append(escapeXml(entry.getKey()))
                    .append("</Name><RecordCount>").append(entry.getValue().size())
                    .append("</RecordCount></Dataset>");
        }

        return buildSoapResponse(
            "<GetStatusResponse>" +
            "<Status>Running</Status>" +
            "<DatasetCount>" + dataStore.size() + "</DatasetCount>" +
            "<Datasets>" + datasets + "</Datasets>" +
            "</GetStatusResponse>"
        );
    }

    private void parseNestedElement(Element element, String prefix, Map<String, String> row) {
        NodeList children = element.getChildNodes();
        String currentPrefix = prefix.isEmpty() ? "" : prefix + ".";

        for (int i = 0; i < children.getLength(); i++) {
            Node child = children.item(i);
            if (child instanceof Element) {
                Element childEl = (Element) child;
                String name = childEl.getLocalName() != null ? childEl.getLocalName() : childEl.getNodeName();
                String fullName = currentPrefix + name;

                if (hasChildElements(childEl)) {
                    parseNestedElement(childEl, fullName, row);
                } else {
                    String text = childEl.getTextContent();
                    if (text != null) {
                        row.put(fullName, text.trim());
                    }
                }
            }
        }
    }

    private boolean hasChildElements(Element element) {
        NodeList children = element.getChildNodes();
        for (int i = 0; i < children.getLength(); i++) {
            if (children.item(i) instanceof Element) return true;
        }
        return false;
    }

    private Element getSoapBody(Document doc) {
        NodeList bodyList = doc.getElementsByTagNameNS("http://schemas.xmlsoap.org/soap/envelope/", "Body");
        if (bodyList.getLength() == 0) {
            bodyList = doc.getElementsByTagNameNS("http://www.w3.org/2003/05/soap-envelope", "Body");
        }
        if (bodyList.getLength() == 0) {
            bodyList = doc.getElementsByTagName("Body");
        }
        return bodyList.getLength() > 0 ? (Element) bodyList.item(0) : doc.getDocumentElement();
    }

    private Element getFirstChildElement(Element parent) {
        if (parent == null) return null;
        NodeList children = parent.getChildNodes();
        for (int i = 0; i < children.getLength(); i++) {
            if (children.item(i) instanceof Element) return (Element) children.item(i);
        }
        return null;
    }

    private Element getFirstChildElement(Element parent, String localName) {
        if (parent == null) return null;
        NodeList children = parent.getChildNodes();
        for (int i = 0; i < children.getLength(); i++) {
            if (children.item(i) instanceof Element) {
                Element el = (Element) children.item(i);
                String name = el.getLocalName() != null ? el.getLocalName() : el.getNodeName();
                if (name.contains(":")) name = name.substring(name.indexOf(':') + 1);
                if (localName.equals(name)) return el;
            }
        }
        return null;
    }

    private String getElementText(Element parent, String childName) {
        Element child = getFirstChildElement(parent, childName);
        if (child == null) return null;
        String text = child.getTextContent();
        return text != null ? text.trim() : null;
    }

    private String buildSoapResponse(String bodyContent) {
        return "<?xml version=\"1.0\" encoding=\"UTF-8\"?>" +
            "<soap:Envelope xmlns:soap=\"http://schemas.xmlsoap.org/soap/envelope/\" " +
            "xmlns:di=\"http://enterprise.example.com/data-integration\">" +
            "<soap:Header/>" +
            "<soap:Body>" +
            "<di:" + bodyContent.substring(1) +
            "</soap:Body>" +
            "</soap:Envelope>";
    }

    private String escapeXml(String input) {
        if (input == null) return "";
        return input.replace("&", "&amp;")
                    .replace("<", "&lt;")
                    .replace(">", "&gt;")
                    .replace("\"", "&quot;")
                    .replace("'", "&apos;");
    }

    private void sendSoapFault(HttpExchange exchange, String faultCode, String faultString, int httpStatus) throws IOException {
        String fault = "<?xml version=\"1.0\" encoding=\"UTF-8\"?>" +
            "<soap:Envelope xmlns:soap=\"http://schemas.xmlsoap.org/soap/envelope/\">" +
            "<soap:Body>" +
            "<soap:Fault>" +
            "<faultcode>soap:" + faultCode + "</faultcode>" +
            "<faultstring>" + escapeXml(faultString) + "</faultstring>" +
            "</soap:Fault>" +
            "</soap:Body>" +
            "</soap:Envelope>";

        byte[] responseBytes = fault.getBytes("UTF-8");
        exchange.getResponseHeaders().set("Content-Type", "text/xml; charset=utf-8");
        exchange.sendResponseHeaders(httpStatus, responseBytes.length);
        try (OutputStream os = exchange.getResponseBody()) {
            os.write(responseBytes);
        }
    }
}