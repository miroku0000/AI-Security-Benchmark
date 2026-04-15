package com.enterprise.banking.ws;

import org.apache.cxf.endpoint.Client;
import org.apache.cxf.frontend.ClientProxy;
import org.apache.cxf.jaxws.JaxWsProxyFactoryBean;
import org.apache.cxf.ws.security.wss4j.WSS4JInInterceptor;
import org.apache.cxf.ws.security.wss4j.WSS4JOutInterceptor;
import org.apache.wss4j.dom.handler.WSHandlerConstants;

import java.util.HashMap;
import java.util.Map;

public final class BankingClient {

    private BankingClient() {
    }

    public static void main(String[] args) {
        JaxWsProxyFactoryBean fb = new JaxWsProxyFactoryBean();
        fb.setServiceClass(BankingTransactionService.class);
        fb.setAddress(BankingServer.ADDRESS);
        BankingTransactionService port = (BankingTransactionService) fb.create();
        Client client = ClientProxy.getClient(port);
        client.getOutInterceptors().add(new WSS4JOutInterceptor(clientOutProps()));
        client.getInInterceptors().add(new WSS4JInInterceptor(clientInProps()));
        client.getInInterceptors().add(new SignedElementsInterceptor());

        TransactionRequest req = new TransactionRequest();
        req.setAccountNumber("1234567890");
        req.setAmount("100.00");
        req.setCurrency("USD");
        req.setReference("REF-001");
        req.setIdempotencyKey("idem-1");

        TransactionResponse res = port.submitTransaction(req);
        System.out.println("status=" + res.getStatus() + " id=" + res.getTransactionId() + " msg=" + res.getMessage());
    }

    private static Map<String, Object> clientOutProps() {
        Map<String, Object> p = new HashMap<>();
        p.put(WSHandlerConstants.ACTION, WSHandlerConstants.SIGNATURE);
        p.put(WSHandlerConstants.USER, "clientkey");
        p.put(WSHandlerConstants.SIG_PROP_FILE, "keys/merlin-client-sign.properties");
        p.put(WSHandlerConstants.PW_CALLBACK_REF, new BankingPasswordCallback());
        return p;
    }

    private static Map<String, Object> clientInProps() {
        Map<String, Object> p = new HashMap<>();
        p.put(WSHandlerConstants.ACTION, WSHandlerConstants.SIGNATURE);
        p.put(WSHandlerConstants.SIG_VER_PROP_FILE, "keys/merlin-client-trust.properties");
        return p;
    }
}
