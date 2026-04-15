package com.bank.soap;

import com.bank.soap.model.TransactionRequest;
import com.bank.soap.model.TransactionResponse;
import java.math.BigDecimal;
import java.util.List;
import java.util.UUID;
import javax.annotation.Resource;
import javax.jws.WebService;
import javax.xml.ws.WebServiceContext;
import javax.xml.ws.handler.MessageContext;
import org.w3c.dom.Element;

@WebService(
    serviceName = "BankingTransactionsService",
    portName = "BankingTransactionsPort",
    endpointInterface = "com.bank.soap.BankingTransactionsPort",
    targetNamespace = "urn:com:bank:soap:transactions:v1"
)
public class BankingTransactionsService implements BankingTransactionsPort {
  @Resource
  private WebServiceContext wsContext;

  @Override
  public TransactionResponse processTransaction(TransactionRequest request) {
    TransactionResponse resp = new TransactionResponse();
    resp.setRequestId(request != null ? request.getRequestId() : null);

    if (request == null) {
      resp.setStatus("REJECTED");
      resp.setMessage("Missing request");
      return resp;
    }

    if (isBlank(request.getFromAccount()) || isBlank(request.getToAccount()) || isBlank(request.getCurrency())
        || request.getAmount() == null || request.getAmount().compareTo(BigDecimal.ZERO) <= 0) {
      resp.setStatus("REJECTED");
      resp.setMessage("Invalid transaction fields");
      return resp;
    }

    MessageContext mc = wsContext != null ? wsContext.getMessageContext() : null;
    @SuppressWarnings("unchecked")
    List<Element> signed = mc != null ? (List<Element>) mc.get("com.bank.soap.signedElements") : null;
    if (signed == null || signed.isEmpty()) {
      resp.setStatus("REJECTED");
      resp.setMessage("No signed elements extracted");
      return resp;
    }

    resp.setStatus("ACCEPTED");
    resp.setTransactionId("TX-" + UUID.randomUUID());
    resp.setMessage("Processed");
    return resp;
  }

  private static boolean isBlank(String s) {
    return s == null || s.trim().isEmpty();
  }
}

