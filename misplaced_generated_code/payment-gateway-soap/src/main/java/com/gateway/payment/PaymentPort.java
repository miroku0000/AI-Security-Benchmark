package com.gateway.payment;

import javax.jws.WebMethod;
import javax.jws.WebParam;
import javax.jws.WebService;
import javax.jws.soap.SOAPBinding;

@WebService(
        name = "PaymentPort",
        targetNamespace = "http://payment.gateway.com/soap")
@SOAPBinding(
        style = SOAPBinding.Style.DOCUMENT,
        use = SOAPBinding.Use.LITERAL,
        parameterStyle = SOAPBinding.ParameterStyle.WRAPPED)
public interface PaymentPort {

    @WebMethod(operationName = "processPayment")
    PaymentResponse processPayment(@WebParam(name = "request") PaymentRequest request);
}
