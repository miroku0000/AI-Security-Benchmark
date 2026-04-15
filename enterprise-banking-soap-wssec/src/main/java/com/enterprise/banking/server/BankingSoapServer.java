package com.enterprise.banking.server;

import com.enterprise.banking.security.KeystoreBootstrap;
import com.enterprise.banking.security.SignedElementExtractionInterceptor;
import com.enterprise.banking.service.BankingPortType;
import com.enterprise.banking.service.BankingPortTypeImpl;
import java.nio.file.Path;
import java.util.HashMap;
import java.util.Map;
import org.apache.cxf.jaxws.JaxWsServerFactoryBean;
import org.apache.cxf.ws.security.wss4j.WSS4JInInterceptor;
import org.apache.wss4j.dom.handler.WSHandlerConstants;

public final class BankingSoapServer {

    private BankingSoapServer() {
    }

    public static void main(String[] args) throws Exception {
        Path cryptoDir = Path.of("target/ws-security-crypto");
        KeystoreBootstrap.ensureCryptoDir(cryptoDir);
        Path serverCrypto = KeystoreBootstrap.writeServerCryptoProperties(cryptoDir);

        JaxWsServerFactoryBean sf = new JaxWsServerFactoryBean();
        sf.setServiceClass(BankingPortType.class);
        sf.setServiceBean(new BankingPortTypeImpl());
        sf.setAddress("http://127.0.0.1:9000/banking");
        sf.setBindingId("http://schemas.xmlsoap.org/wsdl/soap/http");

        Map<String, Object> inProps = new HashMap<>();
        inProps.put(WSHandlerConstants.ACTION, WSHandlerConstants.SIGNATURE);
        inProps.put(WSHandlerConstants.SIGNATURE_PROP_FILE, serverCrypto.toString());

        sf.getInInterceptors().add(new WSS4JInInterceptor(inProps));
        sf.getInInterceptors().add(new SignedElementExtractionInterceptor());

        sf.create();
        Thread.currentThread().join();
    }
}
