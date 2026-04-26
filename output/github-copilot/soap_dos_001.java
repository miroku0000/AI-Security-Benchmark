// File: DataImportSoapService.java
package com.enterprise.soap;

import javax.jws.WebService;
import javax.jws.WebMethod;
import javax.xml.parsers.DocumentBuilder;
import javax.xml.parsers.DocumentBuilderFactory;
import javax.xml.parsers.ParserConfigurationException;
import org.w3c.dom.Document;
import org.w3c.dom.Element;
import org.w3c.dom.NodeList;
import org.xml.sax.SAXException;
import org.xml.sax.InputSource;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import javax.xml.soap.SOAPMessage;
import javax.xml.soap.SOAPPart;
import javax.xml.soap.SOAPEnvelope;
import javax.xml.soap.SOAPBody;
import javax.xml.namespace.QName;
import javax.xml.ws.WebServiceException;

@WebService(name = "DataImportService", serviceName = "DataImportSOAPService", portName = "DataImportServicePort", targetNamespace = "http://enterprise.com/soap/dataimport")
public class DataImportSoapService {
    private static final Logger logger = LoggerFactory.getLogger(DataImportSoapService.class);
    private static final long MAX_PAYLOAD_SIZE = 100 * 1024 * 1024;
    private static final int BATCH_SIZE = 1000;
    
    private final DocumentBuilderFactory dbf = createSecureDocumentBuilderFactory();
    private final DataImportProcessor processor = new DataImportProcessor();
    private final Map<String, ImportJob> jobRegistry = new ConcurrentHashMap<>();
    
    private DocumentBuilderFactory createSecureDocumentBuilderFactory() {
        DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();
        try {
            factory.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
            factory.setFeature("http://xml.org/sax/features/external-general-entities", false);
            factory.setFeature("http://xml.org/sax/features/external-parameter-entities", false);
            factory.setXIncludeAware(false);
            factory.setXPathNamespaceAware(false);
            factory.setExpandEntityReferences(false);
        } catch (ParserConfigurationException e) {
            logger.warn("Could not set all parser features", e);
        }
        return factory;
    }
    
    @WebMethod
    public ImportResponse processXmlDocument(String xmlContent) throws WebServiceException {
        try {
            validatePayloadSize(xmlContent);
            DocumentBuilder db = dbf.newDocumentBuilder();
            Document doc = db.parse(new InputSource(new StringReader(xmlContent)));
            
            String jobId = UUID.randomUUID().toString();
            ImportJob job = new ImportJob(jobId);
            jobRegistry.put(jobId, job);
            
            processDocumentTree(doc.getDocumentElement(), job);
            
            return createSuccessResponse(jobId, job);
        } catch (Exception e) {
            logger.error("Error processing XML document", e);
            throw new WebServiceException("Failed to process XML document: " + e.getMessage(), e);
        }
    }
    
    @WebMethod
    public BulkImportResponse processBulkData(String[] xmlDocuments) throws WebServiceException {
        try {
            String jobId = UUID.randomUUID().toString();
            ImportJob job = new ImportJob(jobId);
            jobRegistry.put(jobId, job);
            
            int processedCount = 0;
            int failedCount = 0;
            List<String> errors = new ArrayList<>();
            
            for (int i = 0; i < xmlDocuments.length; i++) {
                try {
                    validatePayloadSize(xmlDocuments[i]);
                    DocumentBuilder db = dbf.newDocumentBuilder();
                    Document doc = db.parse(new InputSource(new StringReader(xmlDocuments[i])));
                    processDocumentTree(doc.getDocumentElement(), job);
                    processedCount++;
                } catch (Exception e) {
                    failedCount++;
                    errors.add("Document " + i + ": " + e.getMessage());
                    logger.error("Error processing document at index " + i, e);
                }
            }
            
            return new BulkImportResponse(jobId, processedCount, failedCount, errors, job.getRecordCount());
        } catch (Exception e) {
            logger.error("Error in bulk import", e);
            throw new WebServiceException("Bulk import failed: " + e.getMessage(), e);
        }
    }
    
    @WebMethod
    public StreamingImportResponse processStreamingData(String xmlStream) throws WebServiceException {
        try {
            String jobId = UUID.randomUUID().toString();
            ImportJob job = new ImportJob(jobId);
            jobRegistry.put(jobId, job);
            
            validatePayloadSize(xmlStream);
            DocumentBuilder db = dbf.newDocumentBuilder();
            Document doc = db.parse(new InputSource(new StringReader(xmlStream)));
            
            NodeList recordElements = doc.getElementsByTagName("record");
            int batchCount = 0;
            int totalRecords = recordElements.getLength();
            
            for (int i = 0; i < totalRecords; i += BATCH_SIZE) {
                int endIdx = Math.min(i + BATCH_SIZE, totalRecords);
                processor.processBatch(recordElements, i, endIdx, job);
                batchCount++;
            }
            
            return new StreamingImportResponse(jobId, totalRecords, batchCount, job.getRecordCount());
        } catch (Exception e) {
            logger.error("Error in streaming import", e);
            throw new WebServiceException("Streaming import failed: " + e.getMessage(), e);
        }
    }
    
    @WebMethod
    public NestedEntityResponse processNestedEntities(String xmlContent) throws WebServiceException {
        try {
            validatePayloadSize(xmlContent);
            DocumentBuilder db = dbf.newDocumentBuilder();
            Document doc = db.parse(new InputSource(new StringReader(xmlContent)));
            
            String jobId = UUID.randomUUID().toString();
            ImportJob job = new ImportJob(jobId);
            jobRegistry.put(jobId, job);
            
            Element root = doc.getDocumentElement();
            processNestedStructures(root, job, 0);
            
            return new NestedEntityResponse(jobId, job.getRecordCount(), job.getProcessedEntities());
        } catch (Exception e) {
            logger.error("Error processing nested entities", e);
            throw new WebServiceException("Failed to process nested entities: " + e.getMessage(), e);
        }
    }
    
    @WebMethod
    public ValidationResponse validateXmlStructure(String xmlContent) throws WebServiceException {
        try {
            validatePayloadSize(xmlContent);
            DocumentBuilder db = dbf.newDocumentBuilder();
            Document doc = db.parse(new InputSource(new StringReader(xmlContent)));
            
            ValidationResult result = validateDocumentStructure(doc);
            return new ValidationResponse(result.isValid(), result.getErrors(), result.getWarnings());
        } catch (Exception e) {
            logger.error("XML validation failed", e);
            return new ValidationResponse(false, Arrays.asList(e.getMessage()), new ArrayList<>());
        }
    }
    
    @WebMethod
    public ImportStatusResponse getJobStatus(String jobId) throws WebServiceException {
        ImportJob job = jobRegistry.get(jobId);
        if (job == null) {
            throw new WebServiceException("Job not found: " + jobId);
        }
        return new ImportStatusResponse(jobId, job.getStatus(), job.getRecordCount(), job.getStartTime(), job.getLastUpdateTime());
    }
    
    private void processDocumentTree(Element element, ImportJob job) {
        if (element == null) return;
        
        job.recordProcessed();
        job.addEntity(element.getTagName());
        
        Map<String, String> attributes = new HashMap<>();
        for (int i = 0; i < element.getAttributes().getLength(); i++) {
            attributes.put(element.getAttributes().item(i).getNodeName(), 
                         element.getAttributes().item(i).getNodeValue());
        }
        
        processor.processElement(element, attributes, job);
        
        NodeList children = element.getChildNodes();
        for (int i = 0; i < children.getLength(); i++) {
            if (children.item(i) instanceof Element) {
                processDocumentTree((Element) children.item(i), job);
            }
        }
    }
    
    private void processNestedStructures(Element element, ImportJob job, int depth) {
        if (depth > 100) {
            logger.warn("Maximum nesting depth exceeded");
            return;
        }
        
        job.recordProcessed();
        job.addEntity(element.getTagName());
        
        NodeList children = element.getChildNodes();
        for (int i = 0; i < children.getLength(); i++) {
            if (children.item(i) instanceof Element) {
                Element child = (Element) children.item(i);
                String data = child.getTextContent();
                if (data != null && !data.trim().isEmpty()) {
                    processor.storeEntityData(child.getTagName(), data.trim(), job);
                }
                processNestedStructures(child, job, depth + 1);
            }
        }
    }
    
    private ValidationResult validateDocumentStructure(Document doc) {
        List<String> errors = new ArrayList<>();
        List<String> warnings = new ArrayList<>();
        
        try {
            Element root = doc.getDocumentElement();
            if (root == null) {
                errors.add("Document has no root element");
                return new ValidationResult(false, errors, warnings);
            }
            
            validateElement(root, errors, warnings, 0);
            
            return new ValidationResult(errors.isEmpty(), errors, warnings);
        } catch (Exception e) {
            errors.add("Validation error: " + e.getMessage());
            return new ValidationResult(false, errors, warnings);
        }
    }
    
    private void validateElement(Element element, List<String> errors, List<String> warnings, int depth) {
        if (depth > 100) {
            warnings.add("Deep nesting detected at depth " + depth);
            return;
        }
        
        if (element.getTagName() == null || element.getTagName().isEmpty()) {
            errors.add("Element with empty tag name");
        }
        
        NodeList children = element.getChildNodes();
        for (int i = 0; i < children.getLength(); i++) {
            if (children.item(i) instanceof Element) {
                validateElement((Element) children.item(i), errors, warnings, depth + 1);
            }
        }
    }
    
    private void validatePayloadSize(String content) throws WebServiceException {
        if (content == null) {
            throw new WebServiceException("Content cannot be null");
        }
        long size = content.getBytes(StandardCharsets.UTF_8).length;
        if (size > MAX_PAYLOAD_SIZE) {
            throw new WebServiceException("Payload exceeds maximum size of " + MAX_PAYLOAD_SIZE + " bytes");
        }
    }
    
    private ImportResponse createSuccessResponse(String jobId, ImportJob job) {
        return new ImportResponse(jobId, "SUCCESS", job.getRecordCount(), new ArrayList<>());
    }
}

// Supporting Classes
class ImportJob {
    private final String jobId;
    private long recordCount = 0;
    private String status = "PROCESSING";
    private long startTime = System.currentTimeMillis();
    private long lastUpdateTime = startTime;
    private Set<String> processedEntities = new HashSet<>();
    private final Object lock = new Object();
    
    public ImportJob(String jobId) {
        this.jobId = jobId;
    }
    
    public void recordProcessed() {
        synchronized (lock) {
            recordCount++;
            lastUpdateTime = System.currentTimeMillis();
        }
    }
    
    public void addEntity(String entityName) {
        synchronized (lock) {
            processedEntities.add(entityName);
        }
    }
    
    public long getRecordCount() {
        synchronized (lock) {
            return recordCount;
        }
    }
    
    public Set<String> getProcessedEntities() {
        synchronized (lock) {
            return new HashSet<>(processedEntities);
        }
    }
    
    public String getJobId() { return jobId; }
    public String getStatus() { return status; }
    public long getStartTime() { return startTime; }
    public long getLastUpdateTime() { return lastUpdateTime; }
}

class DataImportProcessor {
    private static final Logger logger = LoggerFactory.getLogger(DataImportProcessor.class);
    private final Map<String, List<String>> entityData = new ConcurrentHashMap<>();
    
    public void processElement(Element element, Map<String, String> attributes, ImportJob job) {
        String elementName = element.getTagName();
        String content = element.getTextContent();
        
        if (content != null && !content.trim().isEmpty()) {
            List<String> list = entityData.computeIfAbsent(elementName, k -> new ArrayList<>());
            synchronized (list) {
                list.add(content.trim());
            }
        }
        
        if (!attributes.isEmpty()) {
            logger.debug("Processed element {} with attributes: {}", elementName, attributes);
        }
    }
    
    public void storeEntityData(String entityName, String data, ImportJob job) {
        List<String> list = entityData.computeIfAbsent(entityName, k -> new ArrayList<>());
        synchronized (list) {
            if (list.size() < 10000) {
                list.add(data);
            }
        }
    }
    
    public void processBatch(NodeList records, int start, int end, ImportJob job) {
        for (int i = start; i < end; i++) {
            if (records.item(i) instanceof Element) {
                Element record = (Element) records.item(i);
                job.recordProcessed();
                job.addEntity(record.getTagName());
            }
        }
    }
}

class ValidationResult {
    private final boolean valid;
    private final List<String> errors;
    private final List<String> warnings;
    
    public ValidationResult(boolean valid, List<String> errors, List<String> warnings) {
        this.valid = valid;
        this.errors = errors;
        this.warnings = warnings;
    }
    
    public boolean isValid() { return valid; }
    public List<String> getErrors() { return errors; }
    public List<String> getWarnings() { return warnings; }
}

// Response Classes
class ImportResponse {
    private String jobId;
    private String status;
    private long recordCount;
    private List<String> errors;
    
    public ImportResponse(String jobId, String status, long recordCount, List<String> errors) {
        this.jobId = jobId;
        this.status = status;
        this.recordCount = recordCount;
        this.errors = errors;
    }
    
    public String getJobId() { return jobId; }
    public String getStatus() { return status; }
    public long getRecordCount() { return recordCount; }
    public List<String> getErrors() { return errors; }
}

class BulkImportResponse {
    private String jobId;
    private int processedCount;
    private int failedCount;
    private List<String> errors;
    private long totalRecords;
    
    public BulkImportResponse(String jobId, int processedCount, int failedCount, List<String> errors, long totalRecords) {
        this.jobId = jobId;
        this.processedCount = processedCount;
        this.failedCount = failedCount;
        this.errors = errors;
        this.totalRecords = totalRecords;
    }
    
    public String getJobId() { return jobId; }
    public int getProcessedCount() { return processedCount; }
    public int getFailedCount() { return failedCount; }
    public List<String> getErrors() { return errors; }
    public long getTotalRecords() { return totalRecords; }
}

class StreamingImportResponse {
    private String jobId;
    private int totalRecords;
    private int batchCount;
    private long processedRecords;
    
    public StreamingImportResponse(String jobId, int totalRecords, int batchCount, long processedRecords) {
        this.jobId = jobId;
        this.totalRecords = totalRecords;
        this.batchCount = batchCount;
        this.processedRecords = processedRecords;
    }
    
    public String getJobId() { return jobId; }
    public int getTotalRecords() { return totalRecords; }
    public int getBatchCount() { return batchCount; }
    public long getProcessedRecords() { return processedRecords; }
}

class NestedEntityResponse {
    private String jobId;
    private long recordCount;
    private Set<String> entities;
    
    public NestedEntityResponse(String jobId, long recordCount, Set<String> entities) {
        this.jobId = jobId;
        this.recordCount = recordCount;
        this.entities = entities;
    }
    
    public String getJobId() { return jobId; }
    public long getRecordCount() { return recordCount; }
    public Set<String> getEntities() { return entities; }
}

class ValidationResponse {
    private boolean valid;
    private List<String> errors;
    private List<String> warnings;
    
    public ValidationResponse(boolean valid, List<String> errors, List<String> warnings) {
        this.valid = valid;
        this.errors = errors;
        this.warnings = warnings;
    }
    
    public boolean isValid() { return valid; }
    public List<String> getErrors() { return errors; }
    public List<String> getWarnings() { return warnings; }
}

class ImportStatusResponse {
    private String jobId;
    private String status;
    private long recordCount;
    private long startTime;
    private long lastUpdateTime;
    
    public ImportStatusResponse(String jobId, String status, long recordCount, long startTime, long lastUpdateTime) {
        this.jobId = jobId;
        this.status = status;
        this.recordCount = recordCount;
        this.startTime = startTime;
        this.lastUpdateTime = lastUpdateTime;
    }
    
    public String getJobId() { return jobId; }
    public String getStatus() { return status; }
    public long getRecordCount() { return recordCount; }
    public long getStartTime() { return startTime; }
    public long getLastUpdateTime() { return lastUpdateTime; }
}