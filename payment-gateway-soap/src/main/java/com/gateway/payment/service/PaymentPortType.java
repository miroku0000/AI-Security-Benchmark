package com.gateway.payment.service;

import com.gateway.payment.model.PaymentRequest;
import com.gateway.payment.model.PaymentResponse;

import javax.jws.HandlerChain;
import javax.jws.WebMethod;
import javax.jws.WebParam;
import javax.jws.WebService;
import javax.jws.soap.SOAPBinding;

@WebService(name = "PaymentPortType", targetNamespace = "http://gateway.com/payment/ws")
@SOAPBinding(style = SOAPBinding.Style.DOCUMENT, use = SOAPBinding.Use.LITERAL)
@HandlerChain(file = "/META-INF/handler-chain.xml")
public interface PaymentPortType {

    @WebMethod(operationName = "processPayment")
    PaymentResponse processPayment(@WebParam(name = "request") PaymentRequest request);
}
