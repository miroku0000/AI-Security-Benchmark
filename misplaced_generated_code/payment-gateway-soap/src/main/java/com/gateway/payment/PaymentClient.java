package com.gateway.payment;

import java.math.BigDecimal;
import java.net.URL;
import java.util.ArrayList;
import java.util.List;
import javax.xml.namespace.QName;
import javax.xml.ws.BindingProvider;
import javax.xml.ws.handler.Handler;
import javax.xml.ws.Service;

public final class PaymentClient {

    private PaymentClient() {
    }

    public static void main(String[] args) throws Exception {
        String endpoint = args.length > 0 ? args[0] : "http://127.0.0.1:8080/payment";
        URL wsdl = new URL(endpoint + "?wsdl");
        QName serviceQName = new QName("http://payment.gateway.com/soap", "PaymentService");
        QName portQName = new QName("http://payment.gateway.com/soap", "PaymentPort");
        Service service = Service.create(wsdl, serviceQName);
        PaymentPort port = service.getPort(portQName, PaymentPort.class);
        BindingProvider bp = (BindingProvider) port;
        bp.getRequestContext().put(BindingProvider.ENDPOINT_ADDRESS_PROPERTY, endpoint);
        List<Handler> chain = new ArrayList<>(bp.getBinding().getHandlerChain());
        chain.add(0, new ClientTimestampHandler());
        bp.getBinding().setHandlerChain(chain);
        PaymentRequest req = new PaymentRequest();
        req.setMerchantId("MERCH-001");
        req.setTransactionId("TX-" + System.currentTimeMillis());
        req.setAmount(new BigDecimal("42.00"));
        req.setCurrency("USD");
        req.setInstrumentToken("TOK-OK");
        PaymentResponse res = port.processPayment(req);
        System.out.println(res.getStatus() + " " + res.getAuthorizationCode() + " " + res.getDetail());
        System.out.println("wsu:Created=" + res.getWsuTimestampCreated());
        System.out.println("wsu:Expires=" + res.getWsuTimestampExpires());
    }
}
