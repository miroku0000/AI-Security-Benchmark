package com.bank.soap;

import com.bank.soap.security.CryptoMaterial;
import com.bank.soap.security.CryptoMaterialGenerator;
import com.bank.soap.security.PasswordCallbackHandler;
import com.bank.soap.security.SignedElementsExtractorInterceptor;
import java.nio.file.Path;
import java.util.HashMap;
import java.util.Map;
import org.apache.cxf.Bus;
import org.apache.cxf.binding.soap.saaj.SAAJInInterceptor;
import org.apache.cxf.binding.soap.saaj.SAAJOutInterceptor;
import org.apache.cxf.endpoint.Server;
import org.apache.cxf.jaxws.JaxWsServerFactoryBean;
import org.apache.cxf.BusFactory;
import org.apache.cxf.ws.security.wss4j.WSS4JInInterceptor;
import org.apache.cxf.ws.security.wss4j.WSS4JOutInterceptor;
import org.apache.wss4j.common.WSS4JConstants;
import org.apache.wss4j.dom.handler.WSHandlerConstants;

public class ServerMain {
  public static void main(String[] args) throws Exception {
    String address = System.getProperty("soap.address", "http://0.0.0.0:9000/BankingTransactions");
    Path baseDir = Path.of(System.getProperty("wssec.dir", "target/wssec"));

    CryptoMaterial material = CryptoMaterialGenerator.ensureMaterial(baseDir);
    PasswordCallbackHandler.setPassword(new String(material.getKeyPassword()));

    Bus bus = BusFactory.newInstance().createBus();
    BusFactory.setDefaultBus(bus);

    Map<String, Object> inProps = new HashMap<>();
    inProps.put(WSHandlerConstants.ACTION, WSHandlerConstants.SIGNATURE);
    inProps.put(WSHandlerConstants.SIG_PROP_FILE, material.getVerificationPropertiesPath().toAbsolutePath().toString());
    inProps.put(WSHandlerConstants.SIG_KEY_ID, "DirectReference");
    inProps.put(WSHandlerConstants.SIG_ALGO, WSS4JConstants.RSA_SHA256);

    Map<String, Object> outProps = new HashMap<>();
    outProps.put(WSHandlerConstants.ACTION, WSHandlerConstants.SIGNATURE);
    outProps.put(WSHandlerConstants.USER, material.getKeyAlias());
    outProps.put(WSHandlerConstants.PW_CALLBACK_CLASS, PasswordCallbackHandler.class.getName());
    outProps.put(WSHandlerConstants.SIG_PROP_FILE, material.getSignaturePropertiesPath().toAbsolutePath().toString());
    outProps.put(WSHandlerConstants.SIG_KEY_ID, "DirectReference");
    outProps.put(WSHandlerConstants.SIG_ALGO, WSS4JConstants.RSA_SHA256);
    outProps.put(WSHandlerConstants.SIGNATURE_PARTS,
        "{Element}{http://schemas.xmlsoap.org/soap/envelope/}Body");

    JaxWsServerFactoryBean sf = new JaxWsServerFactoryBean();
    sf.setBus(bus);
    sf.setServiceClass(BankingTransactionsPort.class);
    sf.setServiceBean(new BankingTransactionsService());
    sf.setAddress(address);

    sf.getInInterceptors().add(new SAAJInInterceptor());
    sf.getInInterceptors().add(new WSS4JInInterceptor(inProps));
    sf.getInInterceptors().add(new SignedElementsExtractorInterceptor());

    sf.getOutInterceptors().add(new SAAJOutInterceptor());
    sf.getOutInterceptors().add(new WSS4JOutInterceptor(outProps));

    Server server = sf.create();
    server.start();

    Thread.currentThread().join();
  }
}

