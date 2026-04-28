// PaymentService.java
package com.payment.gateway.service;

import javax.jws.WebMethod;
import javax.jws.WebParam;
import javax.jws.WebResult;
import javax.jws.WebService;
import javax.jws.soap.SOAPBinding;

@WebService(
    name = "PaymentService",
    serviceName = "PaymentProcessingService",
    targetNamespace = "http://payment.gateway.com/service"
)
@SOAPBinding(style = SOAPBinding.Style.DOCUMENT, use = SOAPBinding.Use.LITERAL)
public interface PaymentService {

    @WebMethod(operationName = "processPayment")
    @WebResult(name = "paymentResponse", targetNamespace = "http://payment.gateway.com/service")
    PaymentResponse processPayment(
            @WebParam(name = "paymentRequest", targetNamespace = "http://payment.gateway.com/service")
            PaymentRequest request);

    @WebMethod(operationName = "getTransactionStatus")
    @WebResult(name = "statusResponse", targetNamespace = "http://payment.gateway.com/service")
    TransactionStatus getTransactionStatus(
            @WebParam(name = "transactionId", targetNamespace = "http://payment.gateway.com/service")
            String transactionId);
}