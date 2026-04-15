package com.enterprise.banking.ws;

import javax.jws.WebMethod;
import javax.jws.WebParam;
import javax.jws.WebResult;
import javax.jws.WebService;
import javax.jws.soap.SOAPBinding;

@WebService(name = "BankingTransactionService", targetNamespace = "http://ws.banking.enterprise.com/")
@SOAPBinding(style = SOAPBinding.Style.DOCUMENT, use = SOAPBinding.Use.LITERAL)
public interface BankingTransactionService {

    @WebMethod(operationName = "submitTransaction")
    @WebResult(name = "transactionResponse", targetNamespace = "http://ws.banking.enterprise.com/")
    TransactionResponse submitTransaction(
            @WebParam(name = "request", targetNamespace = "http://ws.banking.enterprise.com/")
            TransactionRequest request);
}
