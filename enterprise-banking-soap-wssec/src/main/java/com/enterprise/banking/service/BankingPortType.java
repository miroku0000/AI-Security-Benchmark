package com.enterprise.banking.service;

import com.enterprise.banking.model.TransactionRequest;
import com.enterprise.banking.model.TransactionResponse;
import jakarta.jws.WebMethod;
import jakarta.jws.WebParam;
import jakarta.jws.WebService;

@WebService(
        targetNamespace = "http://banking.enterprise.com/wsdl",
        name = "BankingPortType",
        serviceName = "EnterpriseBankingService",
        portName = "BankingPort"
)
public interface BankingPortType {

    @WebMethod(operationName = "submitTransaction")
    TransactionResponse submitTransaction(
            @WebParam(name = "transactionRequest", targetNamespace = "http://banking.enterprise.com/types")
            TransactionRequest transactionRequest
    );
}
