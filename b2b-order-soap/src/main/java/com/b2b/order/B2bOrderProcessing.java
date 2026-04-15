package com.b2b.order;

import javax.jws.WebMethod;
import javax.jws.WebParam;
import javax.jws.WebResult;
import javax.jws.WebService;
import javax.jws.soap.SOAPBinding;

@WebService(name = "B2bOrderProcessing", targetNamespace = "http://b2b.order.com/soap")
@SOAPBinding(style = SOAPBinding.Style.DOCUMENT, use = SOAPBinding.Use.LITERAL)
public interface B2bOrderProcessing {

    @WebMethod(operationName = "SubmitOrder")
    @WebResult(name = "orderResult", targetNamespace = "http://b2b.order.com/soap")
    OrderProcessingResult submitOrder(
            @WebParam(name = "orderRequest", targetNamespace = "http://b2b.order.com/soap")
            SubmitOrderRequest orderRequest);
}
