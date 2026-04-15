package com.enterprise.integration;

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
