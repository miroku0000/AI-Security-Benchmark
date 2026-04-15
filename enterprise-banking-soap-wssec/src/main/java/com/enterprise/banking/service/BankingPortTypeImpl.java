package com.enterprise.banking.service;

import com.enterprise.banking.model.TransactionRequest;
import com.enterprise.banking.model.TransactionResponse;
import jakarta.jws.WebService;
import java.util.List;
import java.util.UUID;
import org.apache.cxf.message.Message;
import org.apache.cxf.phase.PhaseInterceptorChain;

@WebService(
        serviceName = "EnterpriseBankingService",
        portName = "BankingPort",
        targetNamespace = "http://banking.enterprise.com/wsdl",
        endpointInterface = "com.enterprise.banking.service.BankingPortType"
)
public class BankingPortTypeImpl implements BankingPortType {

    public static final String SIGNED_REFERENCE_URIS = "com.enterprise.banking.SIGNED_REFERENCE_URIS";
    public static final String SIGNATURE_COUNT = "com.enterprise.banking.SIGNATURE_COUNT";

    @Override
    public TransactionResponse submitTransaction(TransactionRequest transactionRequest) {
        Message m = PhaseInterceptorChain.getCurrentMessage();
        @SuppressWarnings("unchecked")
        List<String> refs = m != null ? (List<String>) m.get(SIGNED_REFERENCE_URIS) : null;
        int sigCount = 0;
        if (m != null && m.get(SIGNATURE_COUNT) instanceof Integer i) {
            sigCount = i;
        }

        if (sigCount < 1 || refs == null || refs.isEmpty()) {
            TransactionResponse denied = new TransactionResponse();
            denied.setTransactionId("NONE");
            denied.setStatus("REJECTED");
            denied.setMessage("WS-Security signature required and verified references missing");
            return denied;
        }

        if (transactionRequest.getAmountCents() <= 0) {
            TransactionResponse bad = new TransactionResponse();
            bad.setTransactionId("NONE");
            bad.setStatus("INVALID");
            bad.setMessage("amountCents must be positive");
            return bad;
        }

        String tid = "TXN-" + UUID.randomUUID();
        TransactionResponse ok = new TransactionResponse();
        ok.setTransactionId(tid);
        ok.setStatus("ACCEPTED");
        ok.setMessage("Processed; sigs=" + sigCount + "; refs=" + String.join(",", refs));
        return ok;
    }
}
