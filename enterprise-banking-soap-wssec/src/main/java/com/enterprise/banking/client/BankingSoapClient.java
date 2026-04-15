package com.enterprise.banking.client;

import com.enterprise.banking.model.TransactionRequest;
import com.enterprise.banking.model.TransactionResponse;
import com.enterprise.banking.security.ClientPasswordCallback;
import com.enterprise.banking.security.KeystoreBootstrap;
import com.enterprise.banking.service.BankingPortType;
import java.nio.file.Path;
import java.util.HashMap;
import java.util.Map;
import org.apache.cxf.jaxws.JaxWsProxyFactoryBean;
import org.apache.cxf.ws.security.wss4j.WSS4JOutInterceptor;
import org.apache.wss4j.dom.handler.WSHandlerConstants;

public final class BankingSoapClient {

    private BankingSoapClient() {
    }

    public static void main(String[] args) throws Exception {
        Path cryptoDir = Path.of("target/ws-security-crypto");
        KeystoreBootstrap.ensureCryptoDir(cryptoDir);
        Path clientCrypto = KeystoreBootstrap.writeClientCryptoProperties(cryptoDir);

        JaxWsProxyFactoryBean fb = new JaxWsProxyFactoryBean();
        fb.setServiceClass(BankingPortType.class);
        fb.setAddress("http://127.0.0.1:9000/banking");

        Map<String, Object> outProps = new HashMap<>();
        outProps.put(WSHandlerConstants.ACTION, WSHandlerConstants.SIGNATURE);
        outProps.put(WSHandlerConstants.USER, KeystoreBootstrap.KEY_ALIAS);
        outProps.put(WSHandlerConstants.PW_CALLBACK_CLASS, ClientPasswordCallback.class.getName());
        outProps.put(WSHandlerConstants.SIGNATURE_PROP_FILE, clientCrypto.toString());
        outProps.put(WSHandlerConstants.SIGNATURE_PARTS,
                "{Element}{http://schemas.xmlsoap.org/soap/envelope/}Body");

        fb.getOutInterceptors().add(new WSS4JOutInterceptor(outProps));

        BankingPortType port = (BankingPortType) fb.create();

        TransactionRequest req = new TransactionRequest();
        req.setCorrelationId("CORR-1");
        req.setDebitAccount("1111");
        req.setCreditAccount("2222");
        req.setAmountCents(5000L);
        req.setCurrency("USD");
        req.setMemo("WS-Security signed transfer");

        TransactionResponse res = port.submitTransaction(req);
        System.out.println(res.getStatus() + " " + res.getTransactionId() + " " + res.getMessage());
    }
}
