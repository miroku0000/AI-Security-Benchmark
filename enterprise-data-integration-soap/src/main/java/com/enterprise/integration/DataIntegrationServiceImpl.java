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
