import javax.jws.WebMethod;
import javax.jws.WebParam;
import javax.jws.WebResult;
import javax.jws.WebService;
import javax.jws.soap.SOAPBinding;
import javax.xml.transform.Source;

@WebService(
        name = "DataIntegrationPort",
        targetNamespace = "http://integration.enterprise.com/soap"
)
@SOAPBinding(style = SOAPBinding.Style.DOCUMENT, use = SOAPBinding.Use.LITERAL)
public interface DataIntegrationPort {

    @WebMethod(operationName = "ProcessXmlDocument")
    @WebResult(name = "ImportResult", targetNamespace = "http://integration.enterprise.com/soap")
    ImportResult processXmlDocument(
            @WebParam(name = "document", targetNamespace = "http://integration.enterprise.com/soap")
            Source document
    );

    @WebMethod(operationName = "ProcessLargeXmlPayload")
    @WebResult(name = "ImportResult", targetNamespace = "http://integration.enterprise.com/soap")
    ImportResult processLargeXmlPayload(
            @WebParam(name = "payload", targetNamespace = "http://integration.enterprise.com/soap")
            byte[] payload
    );
}


package com.enterprise.integration;

import javax.annotation.Resource;
import javax.jws.WebService;
import javax.xml.transform.Source;
import javax.xml.ws.WebServiceContext;
import javax.xml.ws.WebServiceException;

@WebService(
        serviceName = "DataIntegrationService",
        portName = "DataIntegrationPort",
        name = "DataIntegrationPort",
        targetNamespace = "http://integration.enterprise.com/soap",
        endpointInterface = "com.enterprise.integration.DataIntegrationPort"
)
public class DataIntegrationServiceImpl implements DataIntegrationPort {

    @Resource
    private WebServiceContext webServiceContext;

    @Override
    public ImportResult processXmlDocument(Source document) {
        Source effective = document;
        if (effective == null) {
            effective = SoapBodySources.firstPayloadSource(webServiceContext);
        }
        if (effective == null) {
            throw new WebServiceException("Missing XML document: provide Source parameter or SOAP body payload");
        }
        return DocumentImportProcessor.process(effective);
    }

    @Override
    public ImportResult processLargeXmlPayload(byte[] payload) {
        return DocumentImportProcessor.processLargePayload(payload);
    }
}


package com.enterprise.integration;

import javax.xml.ws.Endpoint;

public final class DataIntegrationServer {

    private DataIntegrationServer() {
    }

    public static void main(String[] args) throws Exception {
        String url = args.length > 0 ? args[0] : "http://127.0.0.1:8082/data-integration";
        Endpoint.publish(url, new DataIntegrationServiceImpl());
        System.out.println("Enterprise data integration SOAP: " + url + "?wsdl");
        synchronized (DataIntegrationServer.class) {
            DataIntegrationServer.class.wait();
        }
    }
}


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


package com.enterprise.integration;

import javax.xml.bind.annotation.XmlAccessType;
import javax.xml.bind.annotation.XmlAccessorType;
import javax.xml.bind.annotation.XmlElement;
import javax.xml.bind.annotation.XmlRootElement;
import javax.xml.bind.annotation.XmlType;

@XmlAccessorType(XmlAccessType.FIELD)
@XmlType(name = "ImportResult", propOrder = {
        "status", "rootElementLocalName", "totalElementCount", "maxDepth", "entityCount", "message"
})
@XmlRootElement(name = "ImportResult", namespace = "http://integration.enterprise.com/soap")
public class ImportResult {

    @XmlElement(name = "status", namespace = "http://integration.enterprise.com/soap", required = true)
    private String status;

    @XmlElement(name = "rootElementLocalName", namespace = "http://integration.enterprise.com/soap")
    private String rootElementLocalName;

    @XmlElement(name = "totalElementCount", namespace = "http://integration.enterprise.com/soap")
    private long totalElementCount;

    @XmlElement(name = "maxDepth", namespace = "http://integration.enterprise.com/soap")
    private int maxDepth;

    @XmlElement(name = "entityCount", namespace = "http://integration.enterprise.com/soap")
    private long entityCount;

    @XmlElement(name = "message", namespace = "http://integration.enterprise.com/soap")
    private String message;

    public ImportResult() {
    }

    public ImportResult(String status, String rootElementLocalName, long totalElementCount,
                        int maxDepth, long entityCount, String message) {
        this.status = status;
        this.rootElementLocalName = rootElementLocalName;
        this.totalElementCount = totalElementCount;
        this.maxDepth = maxDepth;
        this.entityCount = entityCount;
        this.message = message;
    }

    public String getStatus() {
        return status;
    }

    public void setStatus(String status) {
        this.status = status;
    }

    public String getRootElementLocalName() {
        return rootElementLocalName;
    }

    public void setRootElementLocalName(String rootElementLocalName) {
        this.rootElementLocalName = rootElementLocalName;
    }

    public long getTotalElementCount() {
        return totalElementCount;
    }

    public void setTotalElementCount(long totalElementCount) {
        this.totalElementCount = totalElementCount;
    }

    public int getMaxDepth() {
        return maxDepth;
    }

    public void setMaxDepth(int maxDepth) {
        this.maxDepth = maxDepth;
    }

    public long getEntityCount() {
        return entityCount;
    }

    public void setEntityCount(long entityCount) {
        this.entityCount = entityCount;
    }

    public String getMessage() {
        return message;
    }

    public void setMessage(String message) {
        this.message = message;
    }
}


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