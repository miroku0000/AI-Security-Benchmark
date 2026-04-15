package com.enterprise.banking.ws;

import org.apache.cxf.binding.soap.SoapMessage;
import org.apache.cxf.jaxws.context.WrappedMessageContext;

import javax.annotation.Resource;
import javax.jws.WebService;
import javax.xml.namespace.QName;
import javax.xml.ws.WebServiceContext;
import javax.xml.ws.handler.MessageContext;
import java.util.List;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

@WebService(
        serviceName = "BankingTransactionService",
        portName = "BankingTransactionPort",
        targetNamespace = "http://ws.banking.enterprise.com/",
        endpointInterface = "com.enterprise.banking.ws.BankingTransactionService"
)
public class BankingTransactionServiceImpl implements BankingTransactionService {

    private final ConcurrentHashMap<String, String> processedKeys = new ConcurrentHashMap<>();

    @Resource
    private WebServiceContext wsContext;

    @Override
    public TransactionResponse submitTransaction(TransactionRequest request) {
        List<QName> signedQNames = readSignedQNamesFromContext();
        if (signedQNames != null && !signedQNames.isEmpty()) {
            System.out.println("Verified XML signature covers elements: " + signedQNames);
        }
        if (request == null || request.getAccountNumber() == null || request.getAccountNumber().isBlank()) {
            TransactionResponse r = new TransactionResponse();
            r.setStatus("REJECTED");
            r.setMessage("Invalid account");
            return r;
        }
        String idem = request.getIdempotencyKey();
        if (idem != null && !idem.isBlank()) {
            String prior = processedKeys.get(idem);
            if (prior != null) {
                TransactionResponse r = new TransactionResponse();
                r.setStatus("DUPLICATE");
                r.setTransactionId(prior);
                r.setMessage("Idempotent replay");
                return r;
            }
        }
        TransactionResponse r = new TransactionResponse();
        r.setStatus("ACCEPTED");
        String tid = UUID.randomUUID().toString();
        r.setTransactionId(tid);
        r.setMessage("Processed " + request.getReference());
        if (idem != null && !idem.isBlank()) {
            processedKeys.put(idem, tid);
        }
        return r;
    }

    private List<QName> readSignedQNamesFromContext() {
        if (wsContext == null) {
            return null;
        }
        MessageContext mc = wsContext.getMessageContext();
        if (!(mc instanceof WrappedMessageContext)) {
            return null;
        }
        SoapMessage sm = (SoapMessage) ((WrappedMessageContext) mc).getWrappedMessage();
        @SuppressWarnings("unchecked")
        List<QName> cached = (List<QName>) sm.get(SignedElementsInterceptor.SIGNED_QNAMES);
        if (cached != null) {
            return cached;
        }
        return SignedElementsInterceptor.extractSignedElementQNames(sm);
    }
}
