package com.enterprise.banking.ws;

import org.apache.cxf.BusFactory;
import org.apache.cxf.jaxws.JaxWsServerFactoryBean;
import org.apache.cxf.ws.security.wss4j.WSS4JInInterceptor;
import org.apache.cxf.ws.security.wss4j.WSS4JOutInterceptor;
import org.apache.wss4j.dom.handler.WSHandlerConstants;

import java.util.HashMap;
import java.util.Map;

public final class BankingServer {

    public static final String ADDRESS = "http://localhost:9000/banking";

    private BankingServer() {
    }

    public static void main(String[] args) throws Exception {
        BusFactory.getDefaultBus(true);
        JaxWsServerFactoryBean sf = new JaxWsServerFactoryBean();
        sf.setServiceClass(BankingTransactionService.class);
        sf.setServiceBean(new BankingTransactionServiceImpl());
        sf.setAddress(ADDRESS);
        sf.getInInterceptors().add(new WSS4JInInterceptor(serverInProps()));
        sf.getOutInterceptors().add(new WSS4JOutInterceptor(serverOutProps()));
        sf.getInInterceptors().add(new SignedElementsInterceptor());
        sf.create();
        System.out.println("Banking WS-Security server at " + ADDRESS);
        Thread.currentThread().join();
    }

    private static Map<String, Object> serverInProps() {
        Map<String, Object> p = new HashMap<>();
        p.put(WSHandlerConstants.ACTION, WSHandlerConstants.SIGNATURE);
        p.put(WSHandlerConstants.SIG_VER_PROP_FILE, "keys/merlin-server-trust.properties");
        return p;
    }

    private static Map<String, Object> serverOutProps() {
        Map<String, Object> p = new HashMap<>();
        p.put(WSHandlerConstants.ACTION, WSHandlerConstants.SIGNATURE);
        p.put(WSHandlerConstants.USER, "serverkey");
        p.put(WSHandlerConstants.SIG_PROP_FILE, "keys/merlin-server-sign.properties");
        p.put(WSHandlerConstants.PW_CALLBACK_REF, new BankingPasswordCallback());
        return p;
    }
}
