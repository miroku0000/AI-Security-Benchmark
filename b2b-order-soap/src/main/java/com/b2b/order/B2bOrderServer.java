package com.b2b.order;

import javax.xml.ws.Endpoint;

public final class B2bOrderServer {

    private B2bOrderServer() {
    }

    public static void main(String[] args) throws Exception {
        String url = args.length > 0 ? args[0] : "http://127.0.0.1:8081/b2b-order";
        Endpoint.publish(url, new B2bOrderProcessingImpl());
        System.out.println("B2B order SOAP service: " + url + "?wsdl");
        synchronized (B2bOrderServer.class) {
            B2bOrderServer.class.wait();
        }
    }
}
