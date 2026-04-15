package com.gateway.payment;

import com.sun.xml.ws.transport.http.server.EndpointImpl;
import java.util.Collections;
import javax.xml.ws.Endpoint;

public final class PaymentServer {

    private PaymentServer() {
    }

    public static void main(String[] args) throws Exception {
        String url = args.length > 0 ? args[0] : "http://127.0.0.1:8080/payment";
        PaymentServiceImpl impl = new PaymentServiceImpl();
        Endpoint ep = Endpoint.create(impl);
        EndpointImpl endpoint = (EndpointImpl) ep;
        endpoint.getBinding().setHandlerChain(Collections.singletonList(new TimestampSecurityHandler()));
        endpoint.publish(url);
        System.out.println("Payment gateway: " + url + "?wsdl");
        Object lock = new Object();
        synchronized (lock) {
            lock.wait();
        }
    }
}
