package com.bank.soap;

import com.bank.soap.model.TransactionRequest;
import com.bank.soap.model.TransactionResponse;
import javax.jws.WebMethod;
import javax.jws.WebParam;
import javax.jws.WebResult;
import javax.jws.WebService;
import javax.jws.soap.SOAPBinding;

@WebService(
    name = "BankingTransactionsPort",
    targetNamespace = "urn:com:bank:soap:transactions:v1"
)
@SOAPBinding(parameterStyle = SOAPBinding.ParameterStyle.BARE)
public interface BankingTransactionsPort {
  @WebMethod(operationName = "ProcessTransaction")
  @WebResult(name = "TransactionResponse", targetNamespace = "urn:com:bank:soap:transactions:v1", partName = "response")
  TransactionResponse processTransaction(
      @WebParam(name = "TransactionRequest", targetNamespace = "urn:com:bank:soap:transactions:v1", partName = "request")
      TransactionRequest request
  );
}

